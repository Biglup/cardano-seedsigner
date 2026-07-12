import math

from dataclasses import dataclass
from typing import List
from seedsigner.helpers.ur2.ur_encoder import UREncoder
from seedsigner.helpers.ur2.ur import UR
from seedsigner.helpers.qr import QR
from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants



@dataclass
class BaseQrEncoder:
    qr_density: str = SettingsConstants.DENSITY__MEDIUM


    def __post_init__(self):
        self.qr = QR()


    @property
    def is_complete(self):
        raise Exception("Not implemented in child class")

    @property
    def qr_max_fragment_size(self):
        raise Exception("Not implemented in child class")

    def seq_len(self):
        raise Exception("Not implemented in child class")

    def next_part(self) -> str:
        raise Exception("Not implemented in child class")
    
    def cur_part(self) -> str:
        raise Exception("Not implemented in child class")
    
    def restart(self):
        """No-op here; only used by animated QR encoders."""
        pass

    def _create_parts(self):
        raise Exception("Not implemented in child class")


    def part_to_image(self, part, width, height, border: int = 3, background_color: str = "ffffff"):
        return self.qr.qrimage_io(part, width, height, border, background_color=background_color)


    def next_part_image(self, width=240, height=240, border=3, background_color="bdbdbd"):
        part = self.next_part()
        return self.part_to_image(part, width, height, border, background_color=background_color)




"""**************************************************************************************
    STATIC QR encoders
**************************************************************************************"""
@dataclass
class BaseStaticQrEncoder(BaseQrEncoder):
    def seq_len(self):
        return 1
    
    def cur_part(self) -> str:
        """ static QRs only have a single part, which `next_part` always returns """
        return self.next_part()


    @property
    def is_complete(self):
        return True



@dataclass
class SeedQrEncoder(BaseStaticQrEncoder):
    mnemonic: List[str] = None
    wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH


    def __post_init__(self):
        """Encode the mnemonic in the numeric SeedQR data format: each word as its 4-digit wordlist index."""
        self.wordlist = Seed.get_wordlist(self.wordlist_language_code)
        super().__post_init__()

        self.data = ""
        for word in self.mnemonic:
            index = self.wordlist.index(word)
            self.data += str("%04d" % index)
    

    def next_part(self):
        return self.data



@dataclass
class CompactSeedQrEncoder(SeedQrEncoder):
    def next_part(self):
        """Encode the mnemonic in the binary CompactSeedQR data format.

        Each word becomes its wordlist index zero-padded to 11 bits. The
        BIP-39 checksum bits at the end (word_count // 3 of them) are
        excluded, and the remaining bit string is packed into bytes 8 bits
        at a time. Returns `bytes` so `qrcode` properly recognizes the
        payload as byte data.
        """
        binary_str = ""
        for word in self.mnemonic:
            index = self.wordlist.index(word)

            binary_str += bin(index).split('b')[1].zfill(11)

        checksum_bits = len(self.mnemonic) // 3
        binary_str = binary_str[:-checksum_bits]

        as_bytes = bytearray()
        for i in range(0, math.ceil(len(binary_str) / 8)):
            as_bytes.append(int('0b' + binary_str[i*8:(i+1)*8], 2))
        
        return bytes(as_bytes)



@dataclass
class GenericStaticQrEncoder(BaseStaticQrEncoder):
    data: str = None

    def next_part(self):
        return self.data



"""**************************************************************************************
    Simple animated QR encoders
**************************************************************************************"""
@dataclass
class BaseSimpleAnimatedQREncoder(BaseQrEncoder):
    def __post_init__(self):
        super().__post_init__()
        self.parts = []
        self.part_num_sent = 0
        self.sent_complete = False
        self._create_parts()


    @property
    def is_complete(self):
        return self.sent_complete


    def seq_len(self):
        return len(self.parts)


    def next_part(self) -> str:
        """Return the next part, wrapping back to the first after the last.

        The encoder is marked complete once the final part in the list has
        been returned.
        """
        if self.part_num_sent > (len(self.parts) - 1):
            self.part_num_sent = 0

        part = self.parts[self.part_num_sent]

        if self.part_num_sent == (len(self.parts) - 1):
            self.sent_complete = True

        self.part_num_sent += 1

        return part


    def cur_part(self) -> str:
        """Re-return the current part, rewinding to the last part when at the start."""
        if self.part_num_sent == 0:
            self.part_num_sent = len(self.parts) - 1
        else:
            self.part_num_sent -= 1
        return self.next_part()


    def restart(self) -> str:
        self.part_num_sent = 0



"""**************************************************************************************
    Fountain encoded animated QR encoders
**************************************************************************************"""
@dataclass
class BaseFountainQrEncoder(BaseQrEncoder):
    def __post_init__(self):
        super().__post_init__()

        self.ur2_encode: UREncoder = None


    @property
    def is_complete(self):
        return self.ur2_encode.is_complete()


    @property
    def qr_max_fragment_size(self):
        density_mapping = {
            SettingsConstants.DENSITY__LOW: 10,
            SettingsConstants.DENSITY__MEDIUM: 30,
            SettingsConstants.DENSITY__HIGH: 120,
        }
        return density_mapping.get(self.qr_density, 30)


    def _create_parts(self):
        """ parts are dynamically generated by the fountain encoder """
        pass


    def seq_len(self):
        return self.ur2_encode.fountain_encoder.seq_len()


    def next_part(self) -> str:
        return self.ur2_encode.next_part().upper()


    def cur_part(self) -> str:
        return self.ur2_encode.current_part().upper()
    

    def restart(self):
        self.ur2_encode.fountain_encoder.restart()



@dataclass
class CardanoAccountQrEncoder(BaseFountainQrEncoder):
    """Animated UR encoder that wraps a CardanoAccountResponse as a
    cardano-account UR and fountain-encodes it for animated display."""
    response: "CardanoAccountResponse" = None

    def __post_init__(self):
        super().__post_init__()
        qr_ur_bytes = UR("cardano-account", bytearray(self.response.to_cbor()))
        self.ur2_encode = UREncoder(ur=qr_ur_bytes, max_fragment_len=self.qr_max_fragment_size)


@dataclass
class CardanoTxSigResponseQrEncoder(BaseFountainQrEncoder):
    """Animated UR encoder for a CardanoTxSignResponse (vkey witness set),
    transmitted back to the host as a cardano-tx-sig-res UR."""
    response: "CardanoTxSignResponse" = None

    def __post_init__(self):
        super().__post_init__()
        qr_ur_bytes = UR("cardano-tx-sig-res", bytearray(self.response.to_cbor()))
        self.ur2_encode = UREncoder(ur=qr_ur_bytes, max_fragment_len=self.qr_max_fragment_size)


@dataclass
class CardanoCip8SigResponseQrEncoder(BaseFountainQrEncoder):
    """Animated UR encoder for a CardanoCip8SignResponse (COSE_Sign1 + COSE_Key),
    transmitted back to the host as a cardano-cip8-sig-res UR."""
    response: "CardanoCip8SignResponse" = None

    def __post_init__(self):
        super().__post_init__()
        qr_ur_bytes = UR("cardano-cip8-sig-res", bytearray(self.response.to_cbor()))
        self.ur2_encode = UREncoder(ur=qr_ur_bytes, max_fragment_len=self.qr_max_fragment_size)


@dataclass
class CardanoTxSigRequestQrEncoder(BaseFountainQrEncoder):
    """Animated UR encoder for a CardanoSignRequest as a cardano-tx-sig-req UR.

    Used by the host companion (and tests) to transmit a transaction to the
    device for signing; the device decodes it via DecodeQR."""
    request: "CardanoSignRequest" = None

    def __post_init__(self):
        super().__post_init__()
        qr_ur_bytes = UR("cardano-tx-sig-req", bytearray(self.request.to_cbor()))
        self.ur2_encode = UREncoder(ur=qr_ur_bytes, max_fragment_len=self.qr_max_fragment_size)


@dataclass
class CardanoCip8SigRequestQrEncoder(BaseFountainQrEncoder):
    """Animated UR encoder for a CardanoMessageSignRequest as a
    cardano-cip8-sig-req UR (host companion / tests)."""
    request: "CardanoMessageSignRequest" = None

    def __post_init__(self):
        super().__post_init__()
        qr_ur_bytes = UR("cardano-cip8-sig-req", bytearray(self.request.to_cbor()))
        self.ur2_encode = UREncoder(ur=qr_ur_bytes, max_fragment_len=self.qr_max_fragment_size)

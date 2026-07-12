import logging
import re

from enum import IntEnum
from embit import bip39
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol

from seedsigner.helpers.ur2.ur_decoder import URDecoder
from seedsigner.helpers.ur2.ur import UR
from seedsigner.models.qr_type import QRType
from seedsigner.models.seed import Seed
from seedsigner.models.settings import SettingsConstants


logger = logging.getLogger(__name__)


UR_DECODER_QR_TYPES = [
    QRType.CARDANO_ACCOUNT_REQUEST,
    QRType.CARDANO_ACCOUNT,
    QRType.CARDANO_TX_SIG_REQUEST,
    QRType.CARDANO_TX_SIG_RESPONSE,
    QRType.CARDANO_CIP8_SIG_REQUEST,
    QRType.CARDANO_CIP8_SIG_RESPONSE,
]


class DecodeQRStatus(IntEnum):
    """
        Used in DecodeQR to communicate status of adding qr frame/segment
    """
    PART_COMPLETE = 1
    PART_EXISTING = 2
    COMPLETE = 3
    FALSE = 4
    INVALID = 5



class DecodeQR:
    """
        Used to process images or string data from animated qr codes.
    """
    def __init__(self, wordlist_language_code: str = SettingsConstants.WORDLIST_LANGUAGE__ENGLISH):
        self.wordlist_language_code = wordlist_language_code
        self.complete = False
        self.qr_type = None
        self.decoder = None


    def add_image(self, image):
        data = DecodeQR.extract_qr_data(image, is_binary=True)
        if data == None:
            return DecodeQRStatus.FALSE

        return self.add_data(data)


    def add_data(self, data):
        if data == None:
            return DecodeQRStatus.FALSE

        qr_type = DecodeQR.detect_segment_type(data, wordlist_language_code=self.wordlist_language_code)

        if self.qr_type == None:
            self.qr_type = qr_type

            if self.qr_type in UR_DECODER_QR_TYPES:
                self.decoder = URDecoder() # BCUR Decoder

            elif self.qr_type in [QRType.SEED__SEEDQR, QRType.SEED__COMPACTSEEDQR, QRType.SEED__MNEMONIC, QRType.SEED__FOUR_LETTER_MNEMONIC, QRType.SEED__UR2]:
                self.decoder = SeedQrDecoder(wordlist_language_code=self.wordlist_language_code)

            elif self.qr_type == QRType.SETTINGS:
                self.decoder = SettingsQrDecoder()  # Settings config

        elif self.qr_type != qr_type:
            logger.debug(f"Ignoring stray QR frame of type {qr_type}; decode in progress is {self.qr_type}")
            return DecodeQRStatus.FALSE

        if not self.decoder:
            # Did not find any recognizable format
            return DecodeQRStatus.INVALID

        # Process the binary formats first
        if self.qr_type == QRType.SEED__COMPACTSEEDQR:
            rt = self.decoder.add(data, QRType.SEED__COMPACTSEEDQR)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt

        # Convert to string data
        if type(data) == bytes:
            # Should always be bytes, but the test suite has some manual datasets that
            # are strings.
            # TODO: Convert the test suite rather than handle here?
            qr_str = data.decode('utf-8')
        else:
            # it's already str data
            qr_str = data

        if self.qr_type in UR_DECODER_QR_TYPES:
            added_part = self.decoder.receive_part(qr_str)
            if self.decoder.is_complete():
                self.complete = True
                return DecodeQRStatus.COMPLETE
            if added_part:
                return DecodeQRStatus.PART_COMPLETE
            else:
                return DecodeQRStatus.PART_EXISTING

        else:
            # All other formats use the same method signature
            rt = self.decoder.add(qr_str, self.qr_type)
            if rt == DecodeQRStatus.COMPLETE:
                self.complete = True
            return rt


    def get_seed_phrase(self):
        if self.is_seed:
            return self.decoder.get_seed_phrase()


    def get_settings_data(self):
        if self.is_settings:
            return self.decoder.data


    def get_percent_complete(self, weight_mixed_frames: bool = False) -> int:
        if not self.decoder:
            return 0

        if self.qr_type in UR_DECODER_QR_TYPES:
            return int(self.decoder.estimated_percent_complete(weight_mixed_frames=weight_mixed_frames) * 100)

        elif self.decoder.total_segments == 1:
            # The single frame QR formats are all or nothing
            if self.decoder.complete:
                return 100
            else:
                return 0

        else:
            return 0


    @property
    def is_complete(self) -> bool:
        return self.complete


    @property
    def is_invalid(self) -> bool:
        return self.qr_type == QRType.INVALID


    @property
    def is_seed(self):
        return self.qr_type in [
            QRType.SEED__SEEDQR,
            QRType.SEED__COMPACTSEEDQR,
            QRType.SEED__UR2,
            QRType.SEED__MNEMONIC, 
            QRType.SEED__FOUR_LETTER_MNEMONIC,
        ]
    

    @property
    def is_cardano_account_request(self):
        return self.qr_type == QRType.CARDANO_ACCOUNT_REQUEST


    @property
    def is_cardano_account(self):
        return self.qr_type == QRType.CARDANO_ACCOUNT


    def _cardano_result_cbor(self):
        """The reassembled UR CBOR payload, or ValueError if the UR did not
        complete cleanly (a failed fountain reassembly leaves an error, not a
        UR, so callers get a graceful ValueError instead of an AttributeError)."""
        message = self.decoder.result_message()
        if not isinstance(message, UR):
            raise ValueError("UR did not decode to a complete message")
        return message.cbor


    def get_cardano_account_request(self):
        from seedsigner.models.cardano_account import CardanoAccountRequest
        return CardanoAccountRequest.from_cbor(self._cardano_result_cbor())


    def get_cardano_account_response(self):
        from seedsigner.models.cardano_account import CardanoAccountResponse
        return CardanoAccountResponse.from_cbor(self._cardano_result_cbor())


    @property
    def is_cardano_tx_sign_request(self):
        return self.qr_type == QRType.CARDANO_TX_SIG_REQUEST


    @property
    def is_cardano_cip8_sign_request(self):
        return self.qr_type == QRType.CARDANO_CIP8_SIG_REQUEST


    @property
    def is_cardano_tx_sign_response(self):
        return self.qr_type == QRType.CARDANO_TX_SIG_RESPONSE


    @property
    def is_cardano_cip8_sign_response(self):
        return self.qr_type == QRType.CARDANO_CIP8_SIG_RESPONSE


    def get_cardano_tx_sign_request(self):
        from seedsigner.models.cardano_tx import CardanoSignRequest
        return CardanoSignRequest.from_cbor(self._cardano_result_cbor())


    def get_cardano_cip8_sign_request(self):
        from seedsigner.models.cardano_tx import CardanoMessageSignRequest
        return CardanoMessageSignRequest.from_cbor(self._cardano_result_cbor())


    def get_cardano_tx_sign_response(self):
        from seedsigner.models.cardano_tx import CardanoTxSignResponse
        return CardanoTxSignResponse.from_cbor(self._cardano_result_cbor())


    def get_cardano_cip8_sign_response(self):
        from seedsigner.models.cardano_tx import CardanoCip8SignResponse
        return CardanoCip8SignResponse.from_cbor(self._cardano_result_cbor())


    @property
    def is_settings(self):
        return self.qr_type == QRType.SETTINGS


    @staticmethod
    def extract_qr_data(image, is_binary:bool = False) -> str | None:
        if image is None:
            return None

        barcodes = pyzbar.decode(image, symbols=[ZBarSymbol.QRCODE], binary=is_binary)

        # if barcodes:
            # print("--------------- extract_qr_data ---------------")
            # print(barcodes)

        for barcode in barcodes:
            # Only pull and return the first barcode
            return barcode.data


    @staticmethod
    def detect_segment_type(s, wordlist_language_code=None):

        try:
            # Convert to str data
            if type(s) == bytes:
                # Should always be bytes, but the test suite has some manual datasets that
                # are strings.
                # TODO: Convert the test suite rather than handle here?
                s = s.decode('utf-8')

            logger.debug(f"segment string: {s}")
            logger.debug(f"segment string length: {len(s)}")

            # Cardano UR types
            if re.search("^UR:CARDANO-ACCOUNT-REQ/", s, re.IGNORECASE):
                return QRType.CARDANO_ACCOUNT_REQUEST

            elif re.search("^UR:CARDANO-ACCOUNT/", s, re.IGNORECASE):
                return QRType.CARDANO_ACCOUNT

            elif re.search("^UR:CARDANO-TX-SIG-REQ/", s, re.IGNORECASE):
                return QRType.CARDANO_TX_SIG_REQUEST

            elif re.search("^UR:CARDANO-TX-SIG-RES/", s, re.IGNORECASE):
                return QRType.CARDANO_TX_SIG_RESPONSE

            elif re.search("^UR:CARDANO-CIP8-SIG-REQ/", s, re.IGNORECASE):
                return QRType.CARDANO_CIP8_SIG_REQUEST

            elif re.search("^UR:CARDANO-CIP8-SIG-RES/", s, re.IGNORECASE):
                return QRType.CARDANO_CIP8_SIG_RESPONSE

            # Seed
            if re.search(r'\d{48,96}', s):
                return QRType.SEED__SEEDQR

            # config data
            if s.startswith("settings::"):
                return QRType.SETTINGS

            # Seed
            # create 4 letter wordlist only if not PSBT (performance gain)
            wordlist = Seed.get_wordlist(wordlist_language_code)
            try:
                _4LETTER_WORDLIST = [word[:4].strip() for word in wordlist]
            except:
                _4LETTER_WORDLIST = []

            if all(x in wordlist for x in s.strip().split(" ")):
                # checks if all words in list are in BIP-39 word list
                return QRType.SEED__MNEMONIC

            elif all(x in _4LETTER_WORDLIST for x in s.strip().split(" ")):
                # checks if all 4 letter words are in list are in 4 letter BIP-39 word list
                return QRType.SEED__FOUR_LETTER_MNEMONIC

        except UnicodeDecodeError:
            # Probably this isn't meant to be string data; check if it's valid byte data
            # below.
            pass

        # Is it byte data?
        if not isinstance(s, bytes):
            try:
                # TODO: remove this check & conversion once above cast to str is removed
                s = s.encode()
            except UnicodeError:
                # Couldn't convert back to bytes; shouldn't happen
                raise Exception("Conversion to bytes failed")

        # CompactSeedQR entropy bytes: 16 (12w), 20 (15w), 32 (24w)
        if len(s) in (16, 20, 32):
            try:
                bitstream = ""
                for b in s:
                    bitstream += bin(b).lstrip('0b').zfill(8)
                # print(bitstream)

                return QRType.SEED__COMPACTSEEDQR
            except Exception as e:
                # Couldn't extract byte data; assume it's not a byte format
                pass

        return QRType.INVALID

class BaseQrDecoder:
    def __init__(self):
        self.total_segments = None
        self.collected_segments = 0
        self.complete = False

    @property
    def is_complete(self) -> bool:
        return self.complete

    def add(self, segment, qr_type):
        raise Exception("Not implemented in child class")
    
    def get_qr_data(self) -> dict:
        # TODO: standardize this approach across all decoders (example: SignMessageQrDecoder)
        raise Exception("get_qr_data must be implemented in decoder child class")



class BaseSingleFrameQrDecoder(BaseQrDecoder):
    def __init__(self):
        super().__init__()
        self.total_segments = 1



class BaseAnimatedQrDecoder(BaseQrDecoder):
    def __init__(self):
        super().__init__()
        self.segments = []

    def current_segment_num(self, segment) -> int:
        raise Exception("Not implemented in child class")

    def total_segment_nums(self, segment) -> int:
        raise Exception("Not implemented in child class")

    def parse_segment(self, segment) -> str:
        raise Exception("Not implemented in child class")
    
    @property
    def is_valid(self) -> bool:
        return True

    def add(self, segment, qr_type=None):
        if self.total_segments == None:
            self.total_segments = self.total_segment_nums(segment)
            self.segments = [None] * self.total_segments
        elif self.total_segments != self.total_segment_nums(segment):
            raise Exception('Segment total changed unexpectedly')

        current_segment_num = self.current_segment_num(segment)
        if self.segments[current_segment_num - 1] == None:
            self.segments[current_segment_num - 1] = self.parse_segment(segment)
            self.collected_segments += 1
            if self.total_segments == self.collected_segments:
                if self.is_valid:
                    self.complete = True
                    return DecodeQRStatus.COMPLETE
                else:
                    return DecodeQRStatus.INVALID
            return DecodeQRStatus.PART_COMPLETE # new segment added

        return DecodeQRStatus.PART_EXISTING # segment not added because it's already been added



class SeedQrDecoder(BaseSingleFrameQrDecoder):
    """
        Decodes single frame representing a seed.
        Supports SeedSigner SeedQR numeric (wordlist indices) representation of a seed.
        Supports SeedSigner CompactSeedQR entropy byte representation of a seed.
        Supports mnemonic seed phrase string data.
    """
    def __init__(self, wordlist_language_code):
        super().__init__()
        self.seed_phrase = []
        self.wordlist_language_code = wordlist_language_code
        self.wordlist = Seed.get_wordlist(wordlist_language_code)


    def add(self, segment, qr_type=QRType.SEED__SEEDQR):
        # `segment` data will either be bytes or str, depending on the qr_type
        if qr_type == QRType.SEED__SEEDQR:
            try:
                self.seed_phrase = []

                # Parse 12 or 24-word QR code
                num_words = int(len(segment) / 4)
                for i in range(0, num_words):
                    index = int(segment[i * 4: (i*4) + 4])
                    word = self.wordlist[index]
                    self.seed_phrase.append(word)
                if len(self.seed_phrase) > 0:
                    if self.is_valid_bip39_word_count() == False:
                        return DecodeQRStatus.INVALID
                    self.complete = True
                    self.collected_segments = 1
                    return DecodeQRStatus.COMPLETE
                else:
                    return DecodeQRStatus.INVALID
            except Exception as e:
                return DecodeQRStatus.INVALID

        if qr_type == QRType.SEED__COMPACTSEEDQR:
            try:
                self.seed_phrase = bip39.mnemonic_from_bytes(segment).split()
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                logger.exception(repr(e))
                return DecodeQRStatus.INVALID

        elif qr_type == QRType.SEED__MNEMONIC:
            try:
                seed_phrase_list = self.seed_phrase = segment.strip().split(" ")

                # embit mnemonic code to validate
                seed = Seed(seed_phrase_list, passphrase="", wordlist_language_code=self.wordlist_language_code)
                if not seed:
                    # seed is not valid, return invalid
                    return DecodeQRStatus.INVALID
                self.seed_phrase = seed_phrase_list
                if self.is_valid_bip39_word_count() == False:
                        return DecodeQRStatus.INVALID
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                return DecodeQRStatus.INVALID

        elif qr_type == QRType.SEED__FOUR_LETTER_MNEMONIC:
            try:
                seed_phrase_list = segment.strip().split(" ")
                words = []
                for s in seed_phrase_list:
                    # TODO: Pre-calculate this once on startup
                    _4LETTER_WORDLIST = [word[:4].strip() for word in self.wordlist]
                    words.append(self.wordlist[_4LETTER_WORDLIST.index(s)])

                # embit mnemonic code to validate
                seed = Seed(words, passphrase="", wordlist_language_code=self.wordlist_language_code)
                if not seed:
                    # seed is not valid, return invalid
                    return DecodeQRStatus.INVALID
                self.seed_phrase = words
                if self.is_valid_bip39_word_count() == False:
                        return DecodeQRStatus.INVALID
                self.complete = True
                self.collected_segments = 1
                return DecodeQRStatus.COMPLETE
            except Exception as e:
                return DecodeQRStatus.INVALID

        else:
            return DecodeQRStatus.INVALID


    def get_seed_phrase(self):
        if self.complete:
            return self.seed_phrase[:]
        return []


    def is_valid_bip39_word_count(self):
        if len(self.seed_phrase) in (12, 15, 24):
            return True
        return False



class SettingsQrDecoder(BaseSingleFrameQrDecoder):
    """
        Decodes settings data from the SettingsQR Generator.
    """
    def __init__(self):
        super().__init__()
        self.data = None


    def add(self, segment, qr_type=QRType.SETTINGS):
        """
            * Ignores unrecognized settings options.
            * Raises an Exception if a settings value is invalid.

            See `Settings.update()` for info on settings validation, especially for
            missing settings.
        """
        if not segment.startswith("settings::"):
            raise Exception("Invalid SettingsQR data")
        
        # Leave any other parsing or validation up to the Settings class itself.
        # SettingsQR are just ascii data to hand it over as-is.
        self.data = segment

        self.complete = True
        self.collected_segments = 1
        return DecodeQRStatus.COMPLETE




"""
Cardano signing request/response data structures and CBOR codecs.

Covers transaction signing (``cardano-tx-sig-req`` / ``cardano-tx-sig-res``) and
CIP-8 message signing (``cardano-cip8-sig-req`` / ``cardano-cip8-sig-res``).

The message type is identified by the **UR type string** at the transport layer,
and each message body is **untagged CBOR**. This follows the Blockchain Commons
Uniform Resources convention: a top-level UR carries the bare CBOR payload, and a
registry tag (here 88000-88003) is only applied when a structure is embedded
inside another CBOR structure. The tag numbers are recorded per class as the
registry identity, but are not written on-wire. Consistent with the account
export codecs in ``cardano_account.py``.

Each request carries the master fingerprint (``xfp``) per signer so the device
can match a required signer to the loaded seed whose ``Seed.get_fingerprint()``
equals it. This is the same 4-byte BTC BIP-32 value the account export returns
as ``master_fingerprint`` (see ``cardano_account.py``).

Validation limits: ``XFP_LEN`` is the 4-byte BIP-32 master fingerprint length
and ``TX_HASH_LEN`` the 32-byte UTXO transaction hash length.
``MAX_PATH_COMPONENTS`` caps derivation paths at 10 entries (CIP-1852 paths
have 5; the cap rejects abusive inputs), a decoded path must contain at least
one component (an empty path names no key and could not be signed with), and
``MAX_PATH_COMPONENT`` caps each derivation index at 32 bits.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from cometa import CborReader, CborWriter, NetworkId


XFP_LEN = 4
TX_HASH_LEN = 32
MAX_PATH_COMPONENTS = 10
MAX_PATH_COMPONENT = 0xFFFFFFFF


def _write_path(w: "CborWriter", path: list[int]) -> None:
    w.write_start_array(len(path))
    for component in path:
        w.write_int(component)


def _read_path(r: "CborReader") -> list[int]:
    count = r.read_array_len()
    if count == 0:
        raise ValueError("derivation path is empty")
    if count > MAX_PATH_COMPONENTS:
        raise ValueError(f"derivation path too long ({count} > {MAX_PATH_COMPONENTS})")
    path = [r.read_uint() for _ in range(count)]
    r.read_array_end()
    for component in path:
        if component > MAX_PATH_COMPONENT:
            raise ValueError(f"derivation path component out of range: {component}")
    return path


def _check_xfp(xfp: bytes, *, allow_empty: bool) -> bytes:
    if xfp == b"" and allow_empty:
        return xfp
    if len(xfp) != XFP_LEN:
        raise ValueError(f"xfp must be {XFP_LEN} bytes, got {len(xfp)}")
    return xfp



@dataclass
class SigningInput:
    """An input that needs to be signed.

    The device uses the derivation path to locate the signing key.
    The tx_hash + index identify the UTXO being spent.

    A script-locked input (multisig / Plutus) has no single owning key (its
    witnesses arrive via ``extra_signers``), so ``xfp`` and ``path`` are
    optional. An input that does declare a path must also declare the xfp
    that owns it.

    Fields:
        tx_hash: 32-byte transaction hash of the spent UTXO.
        index: output index within that transaction.
        xfp: 4-byte master fingerprint; empty means script-locked.
        path: derivation path (hardened component = value + 0x80000000).
    """
    tx_hash: bytes
    index: int
    xfp: bytes = b""
    path: Optional[list[int]] = None

    def to_cbor(self, w: "CborWriter") -> None:
        _check_xfp(self.xfp, allow_empty=(self.path is None))
        num_entries = (
            2
            + (1 if self.xfp else 0)
            + (1 if self.path is not None else 0)
        )
        w.write_start_map(num_entries)
        w.write_int(1)
        w.write_bytes(self.tx_hash)
        w.write_int(2)
        w.write_int(self.index)
        if self.xfp:
            w.write_int(3)
            w.write_bytes(self.xfp)
        if self.path is not None:
            w.write_int(4)
            _write_path(w, self.path)

    @classmethod
    def from_cbor(cls, r: "CborReader") -> "SigningInput":
        tx_hash = index = path = None
        xfp = b""
        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                tx_hash = r.read_bytes()
            elif key == 2:
                index = r.read_uint()
            elif key == 3:
                xfp = r.read_bytes()
            elif key == 4:
                path = _read_path(r)
            else:
                r.skip_value()
        r.read_map_end()
        if tx_hash is None or index is None:
            raise ValueError("SigningInput missing required field (keys 1-2)")
        if len(tx_hash) != TX_HASH_LEN:
            raise ValueError(f"SigningInput tx_hash must be {TX_HASH_LEN} bytes, got {len(tx_hash)}")
        _check_xfp(xfp, allow_empty=(path is None))
        return cls(tx_hash=tx_hash, index=index, xfp=xfp, path=path)


@dataclass
class ChangeOutput:
    """A transaction output claimed to be change.

    The device derives the address from `path` and compares it to the
    actual output address in the transaction body. If verification fails,
    the output is treated as external (safe failure mode: user sees
    inflated sending amount rather than missing a spend).

    `xfp` identifies which loaded seed owns this change path (needed when
    multiple seeds are resident). Empty bytes means unspecified.

    Fields:
        index: output index in the transaction body.
        path: derivation path used to verify the address.
        xfp: 4-byte master fingerprint of the seed that owns this change.
    """
    index: int
    path: list[int]
    xfp: bytes = b""

    def to_cbor(self, w: "CborWriter") -> None:
        w.write_start_map(3)
        w.write_int(1)
        w.write_int(self.index)
        w.write_int(2)
        w.write_bytes(self.xfp)
        w.write_int(3)
        _write_path(w, self.path)

    @classmethod
    def from_cbor(cls, r: "CborReader") -> "ChangeOutput":
        index = path = None
        xfp = b""
        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                index = r.read_uint()
            elif key == 2:
                xfp = r.read_bytes()
            elif key == 3:
                path = _read_path(r)
            else:
                r.skip_value()
        r.read_map_end()
        if index is None or path is None:
            raise ValueError("ChangeOutput missing required field (keys 1, 3)")
        _check_xfp(xfp, allow_empty=True)
        return cls(index=index, path=path, xfp=xfp)


@dataclass
class ExtraSigner:
    """An additional signer required by the transaction (e.g. for minting policies).

    Fields:
        xfp: 4-byte master fingerprint of the signing seed.
        path: derivation path of the signing key.
    """
    xfp: bytes
    path: list[int]

    def to_cbor(self, w: "CborWriter") -> None:
        w.write_start_map(2)
        w.write_int(1)
        w.write_bytes(self.xfp)
        w.write_int(2)
        _write_path(w, self.path)

    @classmethod
    def from_cbor(cls, r: "CborReader") -> "ExtraSigner":
        xfp = path = None
        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                xfp = r.read_bytes()
            elif key == 2:
                path = _read_path(r)
            else:
                r.skip_value()
        r.read_map_end()
        if xfp is None or path is None:
            raise ValueError("ExtraSigner missing required field (keys 1, 2)")
        _check_xfp(xfp, allow_empty=False)
        return cls(xfp=xfp, path=path)


@dataclass
class CardanoSignRequest:
    """Top-level signing request decoded from a UR QR code.

    UR type: cardano-tx-sig-req (registry id 88000; body is untagged CBOR)

    CDDL:
        CardanoSignRequest = {
            1: tstr,                ; request_id (UUID)
            ? 2: tstr,              ; origin (optional wallet name)
            3: bstr,                ; sign_data (transaction body CBOR)
            4: [* SigningInput],    ; inputs
            5: [* ChangeOutput],    ; change_outputs
            6: [* ExtraSigner],     ; extra_signers
            7: uint,                ; network (0 = testnet, 1 = mainnet)
            ? 8: SignerPath         ; collateral_return_path
        }
        SignerPath = {1: bstr .size 4, 2: [*uint]}   ; same shape as ExtraSigner

    Key 8 declares that the transaction body's collateral_return output
    (body key 16) pays back to this wallet: the device derives the address
    from the path and, only if it matches, badges the collateral return as
    a verified own address. Absent or mismatched, the collateral return is
    shown as an external output (safe failure mode).

    `request_id` is a UUID used to correlate request and response; `origin`
    is the requesting wallet's name (e.g. "Eternl", "Lace").
    """
    request_id: str
    origin: Optional[str]
    sign_data: bytes
    inputs: list[SigningInput]
    change_outputs: list[ChangeOutput]
    network: NetworkId
    extra_signers: list[ExtraSigner] = field(default_factory=list)
    collateral_return_path: Optional[ExtraSigner] = None

    def to_cbor(self) -> bytes:
        w = CborWriter()
        num_entries = (
            6
            + (1 if self.origin is not None else 0)
            + (1 if self.collateral_return_path is not None else 0)
        )
        w.write_start_map(num_entries)
        w.write_int(1)
        w.write_str(self.request_id)
        if self.origin is not None:
            w.write_int(2)
            w.write_str(self.origin)
        w.write_int(3)
        w.write_bytes(self.sign_data)
        w.write_int(4)
        w.write_start_array(len(self.inputs))
        for signing_input in self.inputs:
            signing_input.to_cbor(w)
        w.write_int(5)
        w.write_start_array(len(self.change_outputs))
        for change_output in self.change_outputs:
            change_output.to_cbor(w)
        w.write_int(6)
        w.write_start_array(len(self.extra_signers))
        for extra_signer in self.extra_signers:
            extra_signer.to_cbor(w)
        w.write_int(7)
        w.write_int(int(self.network))
        if self.collateral_return_path is not None:
            w.write_int(8)
            self.collateral_return_path.to_cbor(w)
        return w.encode()

    @classmethod
    def from_cbor(cls, data: bytes) -> "CardanoSignRequest":
        try:
            return cls._from_cbor(data)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"malformed cardano-tx-sig-req: {e}") from e

    @classmethod
    def _from_cbor(cls, data: bytes) -> "CardanoSignRequest":
        r = CborReader.from_bytes(data)
        request_id = sign_data = network = None
        origin = None
        inputs: list[SigningInput] = []
        change_outputs: list[ChangeOutput] = []
        extra_signers: list[ExtraSigner] = []
        collateral_return_path: Optional[ExtraSigner] = None

        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                request_id = r.read_str()
            elif key == 2:
                origin = r.read_str()
            elif key == 3:
                sign_data = r.read_bytes()
            elif key == 4:
                inputs = [SigningInput.from_cbor(r) for _ in range(r.read_array_len())]
                r.read_array_end()
            elif key == 5:
                change_outputs = [ChangeOutput.from_cbor(r) for _ in range(r.read_array_len())]
                r.read_array_end()
            elif key == 6:
                extra_signers = [ExtraSigner.from_cbor(r) for _ in range(r.read_array_len())]
                r.read_array_end()
            elif key == 7:
                network = NetworkId(r.read_uint())
            elif key == 8:
                collateral_return_path = ExtraSigner.from_cbor(r)
            else:
                r.skip_value()
        r.read_map_end()

        if request_id is None:
            raise ValueError("cardano-tx-sig-req missing request_id (key 1)")
        if sign_data is None:
            raise ValueError("cardano-tx-sig-req missing sign_data (key 3)")
        if network is None:
            raise ValueError("cardano-tx-sig-req missing network (key 7)")
        has_pathless_input = any(si.path is None for si in inputs)
        has_attributed_signer = bool(extra_signers) or any(si.path is not None for si in inputs)
        if has_pathless_input and not has_attributed_signer:
            raise ValueError(
                "cardano-tx-sig-req declares no signer at all: every input is "
                "script-locked (no signing path) and extra_signers is empty")

        return cls(
            request_id=request_id,
            origin=origin,
            sign_data=sign_data,
            inputs=inputs,
            change_outputs=change_outputs,
            network=network,
            extra_signers=extra_signers,
            collateral_return_path=collateral_return_path,
        )


@dataclass
class CardanoTxSignResponse:
    """The device's reply carrying the vkey witness set.

    UR type: ``cardano-tx-sig-res`` (registry id 88002; body is untagged CBOR).

    CDDL:
        CardanoTxSignResponse = {
            1: tstr,            ; request_id (echoed)
            2: bstr             ; vkey_witness_set_cbor
        }

    Key 2 is a cometa ``VkeyWitnessSet`` serialized to CBOR (a tag-258 set of
    vkey witnesses), NOT a full ``TransactionWitnessSet`` map. The host decodes
    it with ``VkeyWitnessSet.from_cbor`` and applies it to the transaction.
    """
    request_id: str
    vkey_witness_set: bytes

    def to_cbor(self) -> bytes:
        w = CborWriter()
        w.write_start_map(2)
        w.write_int(1)
        w.write_str(self.request_id)
        w.write_int(2)
        w.write_bytes(self.vkey_witness_set)
        return w.encode()

    @classmethod
    def from_cbor(cls, data: bytes) -> "CardanoTxSignResponse":
        try:
            return cls._from_cbor(data)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"malformed cardano-tx-sig-res: {e}") from e

    @classmethod
    def _from_cbor(cls, data: bytes) -> "CardanoTxSignResponse":
        r = CborReader.from_bytes(data)
        request_id = None
        vkey_witness_set = None
        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                request_id = r.read_str()
            elif key == 2:
                vkey_witness_set = r.read_bytes()
            else:
                r.skip_value()
        r.read_map_end()
        if request_id is None:
            raise ValueError("cardano-tx-sig-res missing request_id (key 1)")
        if vkey_witness_set is None:
            raise ValueError("cardano-tx-sig-res missing vkey_witness_set (key 2)")
        return cls(request_id=request_id, vkey_witness_set=vkey_witness_set)


class CardanoParsedTx:
    """Holds the parsed cometa TransactionBody + verified change indices.

    Views access cometa objects directly; there are no wrapper dataclasses.
    Beyond the primary sections, properties expose the remaining transaction
    body fields (CBOR keys 3, 7, 8, 11, 14-17, 21-22) such as ttl,
    auxiliary_data_hash, script_data_hash, required_signers, collateral
    return and treasury/donation values.

    Construction raises ValueError when the body carries the pre-Conway
    protocol parameter update field (key 6). Conway-era Cardano replaced
    that mechanism with governance proposals, the device has no review page
    for it, and nothing consequential may be hidden from the user, so the
    request is refused like any other unreadable transaction.

    `collateral_return_verified` is True when the request's
    collateral_return_path derives to the body's collateral_return address.
    `owned_key_hashes` holds the blake2b-224 hashes of every public key
    derivable from the request's declared paths for the selected seed;
    a credential hash found in this set is cryptographically proven to
    belong to this wallet.
    """

    def __init__(self, sign_request: CardanoSignRequest, verified_change_indices: list[int]):
        from cometa import CborReader, TransactionBody
        reader = CborReader.from_bytes(sign_request.sign_data)
        self.body = TransactionBody.from_cbor(reader)
        if self.body.update is not None:
            raise ValueError(
                "transaction body contains a pre-Conway protocol parameter "
                "update (key 6), which this device cannot display")
        self.sign_request = sign_request
        self.verified_change_indices = verified_change_indices
        self.collateral_return_verified = False
        self.owned_key_hashes: set = set()
        self.unverified_warning_acknowledged = False
        self.network_mismatch_error = (
            self.body.network_id is not None
            and self.body.network_id != sign_request.network
        )

    @property
    def outputs(self):
        return self.body.outputs

    @property
    def fee(self):
        return self.body.fee

    @property
    def certificates(self):
        return self.body.certificates

    @property
    def withdrawals(self):
        return self.body.withdrawals

    @property
    def mint(self):
        return self.body.mint

    @property
    def voting_procedures(self):
        return self.body.voting_procedures

    @property
    def proposals(self):
        return self.body.proposal_procedures

    @property
    def collateral(self):
        return self.body.collateral

    @property
    def reference_inputs(self):
        return self.body.reference_inputs

    @property
    def inputs(self):
        return self.body.inputs

    @property
    def sending_amount(self) -> int:
        total = 0
        for i, output in enumerate(self.outputs):
            if i not in self.verified_change_indices:
                total += output.value.coin
        return total

    @property
    def num_recipients(self) -> int:
        return len(self.outputs) - len(self.verified_change_indices)

    @property
    def has_unverified_outputs(self) -> bool:
        """True when no output could be verified as belonging to this wallet.

        Every amount is then shown as leaving; a total \"sending\" figure would
        be a net the device cannot prove, so callers switch to per-output
        display and surface a notice.
        """
        return len(self.outputs) > 0 and not self.verified_change_indices

    @property
    def has_failed_change_claims(self) -> bool:
        """True when the request declared change output(s) that did NOT verify
        against this seed, a stronger signal than merely having no change
        (which is normal for send-all and multisig transactions): the host
        claimed an output was ours and the claim failed.
        """
        return any(change_output.index not in self.verified_change_indices
                   for change_output in self.sign_request.change_outputs)

    @property
    def output_amounts(self) -> list[int]:
        return [output.value.coin for output in self.outputs]

    @property
    def change_amount(self) -> int:
        return sum(self.outputs[i].value.coin for i in self.verified_change_indices)

    @property
    def sending_tokens(self) -> dict:
        from cometa import Blake2bHash, Bech32
        tokens = {}
        for i, output in enumerate(self.outputs):
            if i not in self.verified_change_indices:
                ma = output.value.multi_asset
                if ma:
                    for policy_id, asset_map in ma.items():
                        for asset_name, qty in asset_map.items():
                            data = policy_id.to_bytes() + asset_name.to_bytes()
                            h = Blake2bHash.compute(data, hash_size=20)
                            key = Bech32.encode("asset", h.to_bytes())
                            tokens[key] = tokens.get(key, 0) + qty
        return tokens

    @property
    def recipient_addresses(self) -> list[str]:
        return [str(self.outputs[i].address) for i in range(len(self.outputs))
                if i not in self.verified_change_indices]

    @property
    def network(self) -> NetworkId:
        return self.sign_request.network

    @property
    def has_certificates(self):
        return self.certificates is not None and len(self.certificates) > 0

    @property
    def has_withdrawals(self):
        return self.withdrawals is not None and len(self.withdrawals) > 0

    @property
    def has_minting(self):
        return self.mint is not None and len(self.mint) > 0

    @property
    def has_voting(self):
        return (self.voting_procedures is not None
                and len(self.voting_procedures.get_voters()) > 0)

    @property
    def has_proposals(self):
        return self.proposals is not None and len(self.proposals) > 0

    @property
    def has_collateral(self):
        return self.collateral is not None and len(self.collateral) > 0

    @property
    def has_reference_inputs(self):
        return self.reference_inputs is not None and len(self.reference_inputs) > 0

    @property
    def ttl(self):
        return self.body.invalid_after

    @property
    def auxiliary_data_hash(self):
        return self.body.aux_data_hash

    @property
    def validity_interval_start(self):
        return self.body.invalid_before

    @property
    def script_data_hash(self):
        return self.body.script_data_hash

    @property
    def required_signers(self):
        return self.body.required_signers

    @property
    def network_id_field(self):
        return self.body.network_id

    @property
    def collateral_return(self):
        return self.body.collateral_return

    @property
    def total_collateral(self):
        return self.body.total_collateral

    @property
    def treasury_value(self):
        return self.body.treasury_value

    @property
    def donation(self):
        return self.body.donation

    @property
    def has_ttl(self):
        return self.ttl is not None

    @property
    def has_auxiliary_data_hash(self):
        return self.auxiliary_data_hash is not None

    @property
    def has_validity_interval_start(self):
        return self.validity_interval_start is not None

    @property
    def has_script_data_hash(self):
        return self.script_data_hash is not None

    @property
    def has_required_signers(self):
        rs = self.required_signers
        return rs is not None and len(rs) > 0

    @property
    def has_network_id_field(self):
        return self.network_id_field is not None

    @property
    def has_collateral_return(self):
        return self.collateral_return is not None

    @property
    def has_total_collateral(self):
        return self.total_collateral is not None

    @property
    def has_treasury(self):
        return self.treasury_value is not None

    @property
    def has_donation(self):
        return self.donation is not None

    def build_review_pages(self) -> list:
        """Build a flat ordered list of all review pages in CBOR key order.

        Section to transaction body CBOR key: outputs 1, fee 2 (always
        present), then the validity window shown as Valid From (key 8)
        followed by Valid Until (key 3), certificates 4, withdrawals 5,
        auxiliary data hash 7, mint 9, script data hash 11, collateral 13
        (individual inputs shown only when total_collateral is absent),
        required signers 14, network id 15, collateral return 16, total
        collateral 17, reference inputs 18, voting procedures 19,
        proposals 20, treasury 21, donation 22.

        The pre-Conway protocol parameter update (key 6) never gets a page:
        a body carrying it is rejected at construction time.
        """
        pages = []

        n = len(self.outputs)
        for i, output in enumerate(self.outputs):
            pages.append(ReviewPage("output", i, n, output))

        pages.append(ReviewPage("fee", 0, 1, self.fee))

        if self.has_validity_interval_start:
            pages.append(ReviewPage("validity_start", 0, 1, self.validity_interval_start))
        if self.has_ttl:
            pages.append(ReviewPage("ttl", 0, 1, self.ttl))

        if self.has_certificates:
            certs = list(self.certificates)
            for i, cert in enumerate(certs):
                pages.append(ReviewPage("certificate", i, len(certs), cert))

        if self.has_withdrawals:
            items = list(self.withdrawals.items())
            for i, item in enumerate(items):
                pages.append(ReviewPage("withdrawal", i, len(items), item))

        if self.has_auxiliary_data_hash:
            pages.append(ReviewPage("aux_data_hash", 0, 1, self.auxiliary_data_hash))

        if self.has_minting:
            items = list(self.mint.items())
            for i, item in enumerate(items):
                pages.append(ReviewPage("mint", i, len(items), item))

        if self.has_script_data_hash:
            pages.append(ReviewPage("script_data_hash", 0, 1, self.script_data_hash))

        if self.has_collateral and not self.has_total_collateral:
            items = list(self.collateral)
            for i, inp in enumerate(items):
                pages.append(ReviewPage("collateral", i, len(items), inp))

        if self.has_required_signers:
            signers = list(self.required_signers)
            for i, signer in enumerate(signers):
                pages.append(ReviewPage("required_signer", i, len(signers), signer))

        if self.has_network_id_field:
            pages.append(ReviewPage("network_id", 0, 1, self.network_id_field))

        if self.has_collateral_return:
            pages.append(ReviewPage("collateral_return", 0, 1, self.collateral_return))

        if self.has_total_collateral:
            pages.append(ReviewPage("total_collateral", 0, 1, self.total_collateral))

        if self.has_reference_inputs:
            items = list(self.reference_inputs)
            for i, inp in enumerate(items):
                pages.append(ReviewPage("reference_input", i, len(items), inp))

        if self.has_voting:
            items = list(self.voting_procedures.items())
            for i, item in enumerate(items):
                pages.append(ReviewPage("voting", i, len(items), item))

        if self.has_proposals:
            proposals = list(self.proposals)
            for i, proposal in enumerate(proposals):
                pages.append(ReviewPage("proposal", i, len(proposals), proposal))

        if self.has_treasury:
            pages.append(ReviewPage("treasury", 0, 1, self.treasury_value))

        if self.has_donation:
            pages.append(ReviewPage("donation", 0, 1, self.donation))

        return pages


@dataclass
class ReviewPage:
    """A single page in the sequential review flow."""
    section: str
    item_index: int
    total_in_section: int
    data: Any


@dataclass
class SigningPath:
    """A derivation path for message signing.

    Hardened path components are encoded as value + 0x80000000.
    """
    index: int
    path: list[int]

    def to_cbor(self, w: "CborWriter") -> None:
        w.write_start_map(2)
        w.write_int(1)
        w.write_int(self.index)
        w.write_int(2)
        _write_path(w, self.path)

    @classmethod
    def from_cbor(cls, r: "CborReader") -> "SigningPath":
        index = path = None
        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                index = r.read_uint()
            elif key == 2:
                path = _read_path(r)
            else:
                r.skip_value()
        r.read_map_end()
        if index is None or path is None:
            raise ValueError("SigningPath missing required field (keys 1, 2)")
        return cls(index=index, path=path)


@dataclass
class CardanoMessageSignRequest:
    """CIP-8 message signing request.

    UR type: cardano-cip8-sig-req (registry id 88001; body is untagged CBOR)

    `xfp` identifies which loaded seed must sign (single-key CIP-8). Empty
    bytes means unspecified. CDDL:
        CardanoCip8SignRequest = {
            1: tstr,                ; request_id (UUID)
            ? 2: tstr,             ; origin (optional wallet name)
            3: bstr,               ; message_payload
            4: bstr,               ; xfp (4 bytes, master fingerprint)
            5: SigningPath,         ; required_signing_path
            ? 6: bstr,             ; address_bytes (sign-with address, optional)
        }
    """
    request_id: str
    origin: Optional[str]
    message_payload: bytes
    required_signing_path: SigningPath
    address_bytes: Optional[bytes] = None
    xfp: bytes = b""

    def to_cbor(self) -> bytes:
        w = CborWriter()
        num_entries = 4 + (1 if self.origin is not None else 0) \
            + (1 if self.address_bytes is not None else 0)
        w.write_start_map(num_entries)
        w.write_int(1)
        w.write_str(self.request_id)
        if self.origin is not None:
            w.write_int(2)
            w.write_str(self.origin)
        w.write_int(3)
        w.write_bytes(self.message_payload)
        w.write_int(4)
        w.write_bytes(self.xfp)
        w.write_int(5)
        self.required_signing_path.to_cbor(w)
        if self.address_bytes is not None:
            w.write_int(6)
            w.write_bytes(self.address_bytes)
        return w.encode()

    @classmethod
    def from_cbor(cls, data: bytes) -> "CardanoMessageSignRequest":
        try:
            return cls._from_cbor(data)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"malformed cardano-cip8-sig-req: {e}") from e

    @classmethod
    def _from_cbor(cls, data: bytes) -> "CardanoMessageSignRequest":
        r = CborReader.from_bytes(data)
        request_id = message_payload = required_signing_path = None
        origin = address_bytes = None
        xfp = b""
        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                request_id = r.read_str()
            elif key == 2:
                origin = r.read_str()
            elif key == 3:
                message_payload = r.read_bytes()
            elif key == 4:
                xfp = r.read_bytes()
            elif key == 5:
                required_signing_path = SigningPath.from_cbor(r)
            elif key == 6:
                address_bytes = r.read_bytes()
            else:
                r.skip_value()
        r.read_map_end()
        if request_id is None:
            raise ValueError("cardano-cip8-sig-req missing request_id (key 1)")
        if message_payload is None:
            raise ValueError("cardano-cip8-sig-req missing message_payload (key 3)")
        if required_signing_path is None:
            raise ValueError("cardano-cip8-sig-req missing required_signing_path (key 5)")
        _check_xfp(xfp, allow_empty=True)
        return cls(
            request_id=request_id,
            origin=origin,
            message_payload=message_payload,
            required_signing_path=required_signing_path,
            address_bytes=address_bytes,
            xfp=xfp,
        )


@dataclass
class CardanoCip8SignResponse:
    """The device's reply carrying the COSE_Sign1 + COSE_Key.

    UR type: ``cardano-cip8-sig-res`` (registry id 88003; body is untagged CBOR).

    CDDL:
        CardanoCip8SignResponse = {
            1: tstr,            ; request_id (echoed)
            2: bstr,            ; cose_sign1_cbor
            3: bstr             ; cose_key_cbor
        }
    """
    request_id: str
    cose_sign1: bytes
    cose_key: bytes

    def to_cbor(self) -> bytes:
        w = CborWriter()
        w.write_start_map(3)
        w.write_int(1)
        w.write_str(self.request_id)
        w.write_int(2)
        w.write_bytes(self.cose_sign1)
        w.write_int(3)
        w.write_bytes(self.cose_key)
        return w.encode()

    @classmethod
    def from_cbor(cls, data: bytes) -> "CardanoCip8SignResponse":
        try:
            return cls._from_cbor(data)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"malformed cardano-cip8-sig-res: {e}") from e

    @classmethod
    def _from_cbor(cls, data: bytes) -> "CardanoCip8SignResponse":
        r = CborReader.from_bytes(data)
        request_id = None
        cose_sign1 = cose_key = None
        for _ in range(r.read_map_len()):
            key = r.read_uint()
            if key == 1:
                request_id = r.read_str()
            elif key == 2:
                cose_sign1 = r.read_bytes()
            elif key == 3:
                cose_key = r.read_bytes()
            else:
                r.skip_value()
        r.read_map_end()
        if request_id is None:
            raise ValueError("cardano-cip8-sig-res missing request_id (key 1)")
        if cose_sign1 is None:
            raise ValueError("cardano-cip8-sig-res missing cose_sign1 (key 2)")
        if cose_key is None:
            raise ValueError("cardano-cip8-sig-res missing cose_key (key 3)")
        return cls(request_id=request_id, cose_sign1=cose_sign1, cose_key=cose_key)

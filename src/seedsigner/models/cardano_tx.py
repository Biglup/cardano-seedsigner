"""
Cardano Transaction Signing Request Data Structures
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from cometa import NetworkId



@dataclass
class SigningInput:
    """An input that needs to be signed.

    The device uses the derivation path to locate the signing key.
    The tx_hash + index identify the UTXO being spent.
    """
    tx_hash: bytes              # 32 bytes - transaction hash of the UTXO
    index: int                  # output index within that transaction
    xfp: bytes                  # 4 bytes - master fingerprint
    path: list[int]             # derivation path components (hardened = val + 0x80000000)


@dataclass
class ChangeOutput:
    """A transaction output claimed to be change.

    The device derives the address from `path` and compares it to the
    actual output address in the transaction body. If verification fails,
    the output is treated as external (safe failure mode: user sees
    inflated sending amount rather than missing a spend).
    """
    index: int                  # output index in the transaction body
    path: list[int]             # derivation path to verify the address


@dataclass
class ExtraSigner:
    """An additional signer required by the transaction (e.g. for minting policies)."""
    xfp: bytes                  # 4 bytes - master fingerprint
    path: list[int]             # derivation path


@dataclass
class CardanoSignRequest:
    """Top-level signing request decoded from a UR QR code.

    UR type: cardano-tx-sig-req (CBOR tag 88000)

    CDDL:
        CardanoSignRequest = {
            1: tstr,                ; request_id (UUID)
            ? 2: tstr,              ; origin (optional wallet name)
            3: bstr,                ; sign_data (transaction body CBOR)
            4: [* SigningInput],    ; inputs
            5: [* ChangeOutput],    ; change_outputs
            6: [* ExtraSigner],     ; extra_signers
            7: uint                 ; network (0 = testnet, 1 = mainnet)
        }
    """
    request_id: str                                  # UUID for tracking
    origin: Optional[str]                            # wallet name (e.g. "Eternl", "Lace")
    sign_data: bytes                                 # raw transaction body CBOR
    inputs: list[SigningInput]                       # inputs that need signing
    change_outputs: list[ChangeOutput]               # change outputs with paths to verify
    network: NetworkId                               # intended network for this transaction
    extra_signers: list[ExtraSigner] = field(default_factory=list)


class CardanoParsedTx:
    """Holds the parsed cometa TransactionBody + verified change indices.

    Views access cometa objects directly — no wrapper dataclasses.
    """

    def __init__(self, sign_request: CardanoSignRequest, verified_change_indices: list[int]):
        from cometa import CborReader, TransactionBody
        reader = CborReader.from_bytes(sign_request.sign_data)
        self.body = TransactionBody.from_cbor(reader)
        self.sign_request = sign_request
        self.verified_change_indices = verified_change_indices
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
        return self.voting_procedures is not None

    @property
    def has_proposals(self):
        return self.proposals is not None and len(self.proposals) > 0

    @property
    def has_collateral(self):
        return self.collateral is not None and len(self.collateral) > 0

    @property
    def has_reference_inputs(self):
        return self.reference_inputs is not None and len(self.reference_inputs) > 0

    # --- Properties for remaining TX body fields (CBOR keys 3, 7, 8, 11, 14-17, 21-22) ---

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

    # --- Flat page list for sequential review ---

    def build_review_pages(self) -> list:
        """Build a flat ordered list of all review pages in CBOR key order."""
        pages = []

        # Key 1: Outputs
        n = len(self.outputs)
        for i, output in enumerate(self.outputs):
            pages.append(ReviewPage("output", i, n, output))

        # Key 2: Fee (always present)
        pages.append(ReviewPage("fee", 0, 1, self.fee))

        # Validity window: Valid From (key 8) then Valid Until (key 3)
        if self.has_validity_interval_start:
            pages.append(ReviewPage("validity_start", 0, 1, self.validity_interval_start))
        if self.has_ttl:
            pages.append(ReviewPage("ttl", 0, 1, self.ttl))

        # Key 4: Certificates
        if self.has_certificates:
            certs = list(self.certificates)
            for i, cert in enumerate(certs):
                pages.append(ReviewPage("certificate", i, len(certs), cert))

        # Key 5: Withdrawals
        if self.has_withdrawals:
            items = list(self.withdrawals.items())
            for i, item in enumerate(items):
                pages.append(ReviewPage("withdrawal", i, len(items), item))

        # Key 7: Auxiliary data hash
        if self.has_auxiliary_data_hash:
            pages.append(ReviewPage("aux_data_hash", 0, 1, self.auxiliary_data_hash))

        # Key 9: Mint
        if self.has_minting:
            items = list(self.mint.items())
            for i, item in enumerate(items):
                pages.append(ReviewPage("mint", i, len(items), item))

        # Key 11: Script data hash
        if self.has_script_data_hash:
            pages.append(ReviewPage("script_data_hash", 0, 1, self.script_data_hash))

        # Key 13: Collateral (only show individual inputs when total_collateral is absent)
        if self.has_collateral and not self.has_total_collateral:
            items = list(self.collateral)
            for i, inp in enumerate(items):
                pages.append(ReviewPage("collateral", i, len(items), inp))

        # Key 14: Required signers
        if self.has_required_signers:
            signers = list(self.required_signers)
            for i, signer in enumerate(signers):
                pages.append(ReviewPage("required_signer", i, len(signers), signer))

        # Key 15: Network ID
        if self.has_network_id_field:
            pages.append(ReviewPage("network_id", 0, 1, self.network_id_field))

        # Key 16: Collateral return
        if self.has_collateral_return:
            pages.append(ReviewPage("collateral_return", 0, 1, self.collateral_return))

        # Key 17: Total collateral
        if self.has_total_collateral:
            pages.append(ReviewPage("total_collateral", 0, 1, self.total_collateral))

        # Key 18: Reference inputs
        if self.has_reference_inputs:
            items = list(self.reference_inputs)
            for i, inp in enumerate(items):
                pages.append(ReviewPage("reference_input", i, len(items), inp))

        # Key 19: Voting procedures
        if self.has_voting:
            items = list(self.voting_procedures.items())
            for i, item in enumerate(items):
                pages.append(ReviewPage("voting", i, len(items), item))

        # Key 20: Proposals
        if self.has_proposals:
            proposals = list(self.proposals)
            for i, proposal in enumerate(proposals):
                pages.append(ReviewPage("proposal", i, len(proposals), proposal))

        # Key 21: Treasury
        if self.has_treasury:
            pages.append(ReviewPage("treasury", 0, 1, self.treasury_value))

        # Key 22: Donation
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
    """A derivation path for message signing."""
    index: int
    path: list[int]  # hardened = val + 0x80000000


@dataclass
class CardanoMessageSignRequest:
    """CIP-8 message signing request.

    UR type: cardano-sign-data-req

    CDDL:
        CardanoSignDataRequest = {
            1: tstr,                ; request_id (UUID)
            ? 2: tstr,             ; origin (optional wallet name)
            3: bstr,               ; message_payload
            ? 4: bstr,             ; address_bytes (optional)
            5: SigningPath,         ; required_signing_path
        }
    """
    request_id: str
    origin: Optional[str]
    message_payload: bytes
    required_signing_path: SigningPath
    address_bytes: Optional[bytes] = None


def format_derivation_path(path: list[int]) -> str:
    """Convert a derivation path to human-readable format.

    e.g. [2147485500, 2147485463, 2147483648, 0, 2] -> "m/1852'/1815'/0'/0/2"
    """
    parts = ["m"]
    for component in path:
        if component >= 0x80000000:
            parts.append(f"{component - 0x80000000}'")
        else:
            parts.append(str(component))
    return "/".join(parts)

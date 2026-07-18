"""
Content-level tests for the mint and proposal review sections.

A zero-quantity mint entry must render as a neutral "0" with no +/- sign and
no mint/burn coloring, and coefficient parameters (pool_pledge_influence a0,
ref_script_cost_per_byte) must render as plain decimals while genuinely
rate-like parameters keep their percentage rendering. Every parameter a
protocol param update can change must appear in the Changes list, including
execution_costs (both price rationals) and cost_models (a presence digest).
Every cometa TransactionBody accessor must likewise be accounted for by
build_review_pages, so no body field can be silently omitted from review.
"""

from unittest.mock import MagicMock, patch

import base  # noqa: F401  (mocks the Raspi hardware modules before seedsigner imports)

from cometa import NetworkId

from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    CardanoParsedTx,
    SigningInput,
)


H = 0x80000000
PATH_PAYMENT = [1852 + H, 1815 + H, H, 0, 0]
ZERO_TX_HASH = b"\x00" * 32

BODY_CBOR_WITH_MINT = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "09" "a1" "581c" + "cc" * 28 +
    "a3" "4141" "00" "4142" "05" "4143" "24"
)

BODY_CBOR_WITH_PARAM_CHANGE = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "14" "81" "84"
    "1a000f4240"
    "581d" "e1" + "aa" * 28 +
    "84" "00" "f6"
    "a4"
    "09" "d81e" "82" "03" "0a"
    "0a" "d81e" "82" "03" "0a"
    "0b" "d81e" "82" "01" "05"
    "1821" "d81e" "82" "0f" "01"
    "f6"
    "82" "69" + b"https://a".hex() + "5820" + "bb" * 32
)

BODY_CBOR_WITH_PLUTUS_PARAM_CHANGE = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "14" "81" "84"
    "1a000f4240"
    "581d" "e1" + "aa" * 28 +
    "84" "00" "f6"
    "a2"
    "12" "a1" "00" "8102"
    "13" "82" "d81e82" "190241" "192710" "d81e82" "1902d1" "1a00989680"
    "f6"
    "82" "69" + b"https://a".hex() + "5820" + "bb" * 32
)


MIN_POLICY_HEX = "29d222ce763455e3d7a09a665ce554f00ac89d2e99a1a83d267170c6"

BODY_CBOR_WITH_VERIFIED_MINT = bytes.fromhex(
    "a4"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 + "1a000f4240"
    "02" "1a0002bf20"
    "09" "a1" "581c" + MIN_POLICY_HEX +
    "a1" "43" "4d494e" "1a002625a0"
)

BODY_CBOR_WITH_VERIFIED_TOKEN_OUTPUT = bytes.fromhex(
    "a3"
    "00" "81" "82" "5820" + "00" * 32 + "00"
    "01" "81" "82" "581d61" + "11" * 28 +
    "82" "1a000f4240"
    "a1" "581c" + MIN_POLICY_HEX + "a1" "43" "4d494e" "1a002625a0"
    "02" "1a0002bf20"
)


def _parsed_tx(sign_data, network=NetworkId.TESTNET):
    request = CardanoSignRequest(
        request_id="content-test",
        origin=None,
        sign_data=sign_data,
        inputs=[SigningInput(tx_hash=ZERO_TX_HASH, index=0,
                             xfp=b"\x00" * 4, path=PATH_PAYMENT)],
        change_outputs=[],
        network=network,
    )
    return CardanoParsedTx(request, verified_change_indices=[])


def _run_section_view(view_cls, parsed_tx, section):
    """Run the section view for `section`'s first page with the screen mocked;
    returns the kwargs the view passed to run_screen()."""
    captured = {}

    def fake_initialize(self):
        self.controller = MagicMock()
        self.settings = MagicMock()
        self.renderer = MagicMock()
        self.canvas_width = 240
        self.canvas_height = 240
        self.screen = None
        self._redirect = None

    def fake_run_screen(self, screen_cls, **kwargs):
        captured.update(kwargs)
        from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
        return RET_CODE__BACK_BUTTON

    with patch("seedsigner.views.view.View._initialize", fake_initialize), \
         patch.object(view_cls, "run_screen", fake_run_screen):
        view = view_cls(parsed_tx=parsed_tx, global_index=0)
        indices = [i for i, page in enumerate(view.pages) if page.section == section]
        assert indices, f"no page for section {section}"
        view.global_index = indices[0]
        view.run()

    return captured


def test_mint_zero_quantity_renders_neutral():
    from seedsigner.views.tx_review.mint_view import MintReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_MINT)
    content = _run_section_view(MintReviewView, parsed, "mint")["content"]
    assert ("value_highlight", "Mint") in content
    assert ("value_large", "0") in content
    assert ("value_large_yes", "+0") not in content
    assert ("value_large_warn", "0") not in content


def test_mint_positive_and_negative_keep_signed_coloring():
    from seedsigner.views.tx_review.mint_view import MintReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_MINT)
    content = _run_section_view(MintReviewView, parsed, "mint")["content"]
    assert ("value_highlight_yes", "Mint") in content
    assert ("value_large_yes", "+5") in content
    assert ("value_highlight_warn", "Burn") in content
    assert ("value_large_warn", "-5") in content


def test_mint_of_verified_asset_shows_ticker_decimals_and_badge():
    from seedsigner.views.tx_review.mint_view import MintReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_VERIFIED_MINT, network=NetworkId.MAINNET)
    content = _run_section_view(MintReviewView, parsed, "mint")["content"]
    assert ("value_highlight", "MIN") in content
    assert ("value_large_yes", "+2.5") in content
    assert ("verified", "Verified") in content


def test_mint_of_verified_asset_stays_raw_on_testnet():
    from seedsigner.views.tx_review.mint_view import MintReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_VERIFIED_MINT, network=NetworkId.TESTNET)
    content = _run_section_view(MintReviewView, parsed, "mint")["content"]
    assert ("value_highlight", "MIN") not in content
    assert ("value_large_yes", "+2,500,000") in content
    assert ("verified", "Verified") not in content


def test_output_tokens_carry_verified_asset_on_mainnet_only():
    from seedsigner.helpers.cardano_utils import asset_fingerprint
    from seedsigner.views.tx_review.output_view import OutputReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_VERIFIED_TOKEN_OUTPUT,
                        network=NetworkId.MAINNET)
    tokens = _run_section_view(OutputReviewView, parsed, "output")["tokens"]
    assert len(tokens) == 1
    fingerprint, qty, verified = tokens[0]
    assert fingerprint.startswith("asset1")
    assert qty == 2500000
    assert verified is not None
    assert verified.ticker == "MIN"
    assert verified.decimals == 6

    parsed = _parsed_tx(BODY_CBOR_WITH_VERIFIED_TOKEN_OUTPUT,
                        network=NetworkId.TESTNET)
    tokens = _run_section_view(OutputReviewView, parsed, "output")["tokens"]
    fingerprint, qty, verified = tokens[0]
    assert qty == 2500000
    assert verified is None


def test_pool_pledge_influence_renders_as_plain_decimal():
    from seedsigner.views.tx_review.proposal_view import ProposalReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_PARAM_CHANGE)
    content = _run_section_view(ProposalReviewView, parsed, "proposal")["content"]
    assert ("value_highlight", "Pledge Influence: 0.3") in content
    assert ("value_highlight", "Pledge Influence: 30%") not in content


def test_ref_script_cost_per_byte_renders_as_plain_decimal():
    from seedsigner.views.tx_review.proposal_view import ProposalReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_PARAM_CHANGE)
    content = _run_section_view(ProposalReviewView, parsed, "proposal")["content"]
    assert ("value_highlight", "Ref Script Cost/Byte: 15") in content
    assert ("value_highlight", "Ref Script Cost/Byte: 1500%") not in content


def test_rate_parameters_still_render_as_percentages():
    from seedsigner.views.tx_review.proposal_view import ProposalReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_PARAM_CHANGE)
    content = _run_section_view(ProposalReviewView, parsed, "proposal")["content"]
    assert ("value_highlight", "Expansion Rate: 30%") in content
    assert ("value_highlight", "Treasury Growth Rate: 20%") in content


def test_execution_costs_render_both_price_rationals():
    from seedsigner.views.tx_review.proposal_view import ProposalReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_PLUTUS_PARAM_CHANGE)
    content = _run_section_view(ProposalReviewView, parsed, "proposal")["content"]
    assert ("value_highlight", "Mem Price: 0.0577") in content
    assert ("value_highlight", "Step Price: 7.21e-05") in content


def test_cost_models_render_presence_digest():
    from seedsigner.views.tx_review.proposal_view import ProposalReviewView

    parsed = _parsed_tx(BODY_CBOR_WITH_PLUTUS_PARAM_CHANGE)
    content = _run_section_view(ProposalReviewView, parsed, "proposal")["content"]
    assert ("value_highlight", "Cost Models: Plutus V1") in content


def test_param_fields_cover_every_protocol_param_update_accessor():
    from cometa import ProtocolParamUpdate

    from seedsigner.views.tx_review.proposal_view import _PARAM_FIELDS

    accessors = {
        name for name in dir(ProtocolParamUpdate)
        if isinstance(getattr(ProtocolParamUpdate, name), property)
    }
    explicitly_rendered = {"pool_voting_thresholds", "drep_voting_thresholds"}
    covered = {name for name, _ in _PARAM_FIELDS} | explicitly_rendered
    assert accessors <= covered, f"unrendered parameters: {accessors - covered}"


def test_review_pages_cover_every_transaction_body_accessor():
    """Every cometa TransactionBody accessor must be surfaced as a review
    page, deliberately excluded, or rejected at parse time, so a new body
    field added by cometa cannot slip past review unnoticed.

    Excluded: `inputs` (key 0) are opaque UTXO pointers the device cannot
    resolve to amounts (the review verifies outputs, fee and collateral
    instead), and `hash` is the computed body digest, not a body field.
    Individual `collateral` inputs are surfaced only when total_collateral
    is absent, but the accessor is still surfaced.

    Rejected: `update` (key 6), the pre-Conway protocol parameter update;
    CardanoParsedTx refuses to construct when it is present.
    """
    from cometa import TransactionBody

    accessors = {
        name for name in dir(TransactionBody)
        if isinstance(getattr(TransactionBody, name), property)
    }
    surfaced = {
        "outputs", "fee", "invalid_before", "invalid_after", "certificates",
        "withdrawals", "aux_data_hash", "mint", "script_data_hash",
        "collateral", "required_signers", "network_id", "collateral_return",
        "total_collateral", "reference_inputs", "voting_procedures",
        "proposal_procedures", "treasury_value", "donation",
    }
    excluded = {"inputs", "hash"}
    rejected = {"update"}
    covered = surfaced | excluded | rejected
    assert accessors <= covered, f"unaccounted body accessors: {accessors - covered}"
    assert covered <= accessors, f"stale accessor names: {covered - accessors}"


class _Bytes:
    def __init__(self, value):
        self._value = value

    def to_bytes(self):
        return self._value


class _Rational:
    def __init__(self, value):
        self._value = value

    def __float__(self):
        return self._value


def test_asset_fingerprint_matches_cip14_vectors():
    from seedsigner.helpers.cardano_utils import asset_fingerprint

    policy = _Bytes(bytes.fromhex("7eae28af2208be856f7a119668ae52a49b73725e326dc16579dcc373"))
    assert asset_fingerprint(policy, _Bytes(b"")) == "asset1rjklcrnsdzqp65wjgrg55sy9723kw09mlgvlc3"
    assert asset_fingerprint(policy, _Bytes(bytes.fromhex("504154415445"))) == \
        "asset13n25uv0yaf5kus35fm2k86cqy60z58d9xmde92"


def test_format_percent_whole_and_fractional():
    from seedsigner.helpers.cardano_utils import format_percent

    assert format_percent(_Rational(0.05)) == "5%"
    assert format_percent(_Rational(0.5)) == "50%"
    assert format_percent(_Rational(0.0275)) == "2.75%"

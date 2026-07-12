"""
Content-level tests for the mint and proposal review sections.

A zero-quantity mint entry must render as a neutral "0" with no +/- sign and
no mint/burn coloring, and coefficient parameters (pool_pledge_influence a0,
ref_script_cost_per_byte) must render as plain decimals while genuinely
rate-like parameters keep their percentage rendering.
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


def _parsed_tx(sign_data):
    request = CardanoSignRequest(
        request_id="content-test",
        origin=None,
        sign_data=sign_data,
        inputs=[SigningInput(tx_hash=ZERO_TX_HASH, index=0,
                             xfp=b"\x00" * 4, path=PATH_PAYMENT)],
        change_outputs=[],
        network=NetworkId.TESTNET,
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

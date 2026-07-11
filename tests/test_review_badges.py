"""
View-level tests for the ownership badges on the transaction review screens.

Builds badge-rich transaction bodies (certificates, withdrawal, required
signers, votes, collateral return) whose credentials belong to the test seed,
runs each section view with the screen mocked, and asserts the exact badge
lines the view hands to its screen.
"""

from unittest.mock import MagicMock, patch

import pytest

import base  # noqa: F401  (mocks the Raspi hardware modules before seedsigner imports)

from cometa import CborWriter, NetworkId

from seedsigner.models.seed import Seed
from seedsigner.models.cardano_tx import (
    CardanoSignRequest,
    CardanoParsedTx,
    SigningInput,
    ExtraSigner,
)
from seedsigner.helpers.cardano_utils import (
    root_key_from_seed,
    verify_change_outputs,
    verify_collateral_return,
    derive_owned_key_hashes,
)


H = 0x80000000
PATH_PAYMENT = [1852 + H, 1815 + H, H, 0, 0]
PATH_STAKE = [1852 + H, 1815 + H, H, 2, 0]
PATH_DREP = [1852 + H, 1815 + H, H, 3, 0]
ZERO_TX_HASH = b"\x00" * 32
FOREIGN_ADDR = bytes.fromhex("60" + "11" * 28)
FOREIGN_KEY_HASH = b"\x22" * 28
FAKE_POOL_KEY_HASH = b"\x33" * 28
FAKE_GOV_ACTION_TX = b"\x44" * 32


@pytest.fixture
def seed():
    return Seed(mnemonic=("abandon " * 11 + "about").split())


def _key_hash(seed, path) -> bytes:
    key = root_key_from_seed(seed).derive(path)
    return key.get_public_key().to_ed25519_key().to_hash().to_bytes()


def _base_addr_bytes(seed) -> bytes:
    from cometa import BaseAddress, Credential
    return BaseAddress.from_credentials(
        NetworkId.TESTNET,
        Credential.from_key_hash(_key_hash(seed, PATH_PAYMENT)),
        Credential.from_key_hash(_key_hash(seed, PATH_STAKE)),
    ).to_bytes()


def _reward_addr_bytes(seed) -> bytes:
    from cometa import RewardAddress, Credential
    return RewardAddress.from_credentials(
        NetworkId.TESTNET,
        Credential.from_key_hash(_key_hash(seed, PATH_STAKE)),
    ).to_bytes()


def _write_key_hash_credential(w, key_hash):
    w.write_start_array(2)
    w.write_int(0)
    w.write_bytes(key_hash)


def _body(seed, certificates=0, withdrawal=False, foreign_withdrawal=False,
          mainnet_withdrawal=False, required_signers=None, vote=False,
          foreign_vote=False, foreign_cert=False, script_cert=False,
          collateral_return=False) -> bytes:
    sections = 3
    sections += 1 if (certificates or foreign_cert or script_cert) else 0
    sections += 1 if (withdrawal or foreign_withdrawal or mainnet_withdrawal) else 0
    sections += 1 if required_signers else 0
    sections += 1 if (vote or foreign_vote) else 0
    sections += 3 if collateral_return else 0

    w = CborWriter()
    w.write_start_map(sections)

    w.write_int(0)
    w.write_start_array(1)
    w.write_start_array(2)
    w.write_bytes(ZERO_TX_HASH)
    w.write_int(0)

    w.write_int(1)
    w.write_start_array(1)
    w.write_start_array(2)
    w.write_bytes(FOREIGN_ADDR)
    w.write_int(1_000_000)

    w.write_int(2)
    w.write_int(180_000)

    if certificates or foreign_cert or script_cert:
        stake_hash = _key_hash(seed, PATH_STAKE)
        w.write_int(4)
        w.write_start_array((3 if certificates else 0)
                            + (1 if foreign_cert else 0)
                            + (1 if script_cert else 0))
        if certificates:
            w.write_start_array(2)
            w.write_int(0)
            _write_key_hash_credential(w, stake_hash)
            w.write_start_array(3)
            w.write_int(2)
            _write_key_hash_credential(w, stake_hash)
            w.write_bytes(FAKE_POOL_KEY_HASH)
            w.write_start_array(4)
            w.write_int(16)
            _write_key_hash_credential(w, _key_hash(seed, PATH_DREP))
            w.write_int(500_000_000)
            w.write_null()
        if foreign_cert:
            w.write_start_array(2)
            w.write_int(0)
            _write_key_hash_credential(w, FOREIGN_KEY_HASH)
        if script_cert:
            w.write_start_array(2)
            w.write_int(0)
            w.write_start_array(2)
            w.write_int(1)
            w.write_bytes(FOREIGN_KEY_HASH)

    if withdrawal or foreign_withdrawal or mainnet_withdrawal:
        w.write_int(5)
        w.write_start_map((1 if withdrawal else 0)
                          + (1 if foreign_withdrawal else 0)
                          + (1 if mainnet_withdrawal else 0))
        if withdrawal:
            w.write_bytes(_reward_addr_bytes(seed))
            w.write_int(3_000_000)
        if foreign_withdrawal:
            w.write_bytes(b"\xe0" + FOREIGN_KEY_HASH)
            w.write_int(1_000_000)
        if mainnet_withdrawal:
            w.write_bytes(b"\xe1" + _key_hash(seed, PATH_STAKE))
            w.write_int(2_000_000)

    if collateral_return:
        w.write_int(13)
        w.write_start_array(1)
        w.write_start_array(2)
        w.write_bytes(ZERO_TX_HASH)
        w.write_int(1)
        w.write_int(16)
        w.write_start_array(2)
        w.write_bytes(_base_addr_bytes(seed))
        w.write_int(5_000_000)
        w.write_int(17)
        w.write_int(2_000_000)

    if required_signers:
        w.write_int(14)
        w.write_start_array(len(required_signers))
        for key_hash in required_signers:
            w.write_bytes(key_hash)

    if vote or foreign_vote:
        w.write_int(19)
        w.write_start_map((1 if vote else 0) + (1 if foreign_vote else 0))
        voter_hashes = []
        if vote:
            voter_hashes.append(_key_hash(seed, PATH_DREP))
        if foreign_vote:
            voter_hashes.append(FOREIGN_KEY_HASH)
        for voter_hash in voter_hashes:
            w.write_start_array(2)
            w.write_int(2)
            w.write_bytes(voter_hash)
            w.write_start_map(1)
            w.write_start_array(2)
            w.write_bytes(FAKE_GOV_ACTION_TX)
            w.write_int(0)
            w.write_start_array(2)
            w.write_int(1)
            w.write_null()

    return w.encode()


def _parsed_tx(seed, sign_data, extra_paths=(), collateral_return=False):
    fp = bytes.fromhex(seed.get_fingerprint())
    request = CardanoSignRequest(
        request_id="badge-test",
        origin=None,
        sign_data=sign_data,
        inputs=[SigningInput(tx_hash=ZERO_TX_HASH, index=0, xfp=fp, path=PATH_PAYMENT)],
        change_outputs=[],
        network=NetworkId.TESTNET,
        extra_signers=[ExtraSigner(xfp=fp, path=list(p)) for p in extra_paths],
        collateral_return_path=ExtraSigner(xfp=fp, path=PATH_PAYMENT)
        if collateral_return else None,
    )
    parsed = CardanoParsedTx(request, verified_change_indices=[])
    parsed.verified_change_indices = verify_change_outputs(request, seed, parsed.body)
    parsed.collateral_return_verified = verify_collateral_return(request, seed, parsed.body)
    parsed.owned_key_hashes = derive_owned_key_hashes(request, seed)
    return parsed


def _run_section_view(view_cls, parsed_tx, section):
    return _run_section_view_at(view_cls, parsed_tx, section, 0)


def test_collateral_return_view_badges_verified_address(seed):
    from seedsigner.views.tx_review.collateral_return_view import CollateralReturnReviewView

    parsed = _parsed_tx(seed, _body(seed, collateral_return=True), collateral_return=True)
    assert parsed.collateral_return_verified
    content = _run_section_view(CollateralReturnReviewView, parsed, "collateral_return")["content"]
    assert ("verified", "Verified Address") in content
    assert ("label_own", "Address (Own):") in content


def test_collateral_return_view_foreign_without_declared_path(seed):
    from seedsigner.views.tx_review.collateral_return_view import CollateralReturnReviewView

    parsed = _parsed_tx(seed, _body(seed, collateral_return=True))
    content = _run_section_view(CollateralReturnReviewView, parsed, "collateral_return")["content"]
    assert ("verified", "Verified Address") not in content
    assert ("label_foreign", "Address (Foreign):") in content


def test_certificate_views_badge_own_credentials(seed):
    from seedsigner.views.tx_review.certificate_view import CertificateReviewView

    parsed = _parsed_tx(seed, _body(seed, certificates=3),
                        extra_paths=[PATH_STAKE, PATH_DREP])
    for cert_index, label in enumerate(
            ["Credential:", "Credential:", "DRep ID:"]):
        content = _run_section_view_at(CertificateReviewView, parsed,
                                       "certificate", cert_index)["content"]
        assert ("verified", "Own Key") in content, f"certificate {cert_index} not badged"
        assert ("label", label) in content


def test_certificate_unknown_credential_is_badged(seed):
    from seedsigner.views.tx_review.certificate_view import CertificateReviewView

    parsed = _parsed_tx(seed, _body(seed, foreign_cert=True))
    content = _run_section_view_at(CertificateReviewView, parsed, "certificate", 0)["content"]
    assert ("label", "Credential:") in content
    assert ("foreign", "Unknown Key") in content
    assert ("verified", "Own Key") not in content


def test_certificate_script_credential_is_unbadged(seed):
    from seedsigner.views.tx_review.certificate_view import CertificateReviewView

    parsed = _parsed_tx(seed, _body(seed, script_cert=True), extra_paths=[PATH_STAKE])
    content = _run_section_view_at(CertificateReviewView, parsed, "certificate", 0)["content"]
    assert ("verified", "Own Key") not in content
    assert ("foreign", "Unknown Key") not in content


def test_certificate_pool_hash_is_not_badged(seed):
    from seedsigner.views.tx_review.certificate_view import CertificateReviewView

    parsed = _parsed_tx(seed, _body(seed, certificates=3),
                        extra_paths=[PATH_STAKE, PATH_DREP])
    content = _run_section_view_at(CertificateReviewView, parsed, "certificate", 1)["content"]
    assert content.count(("verified", "Own Key")) == 1
    assert ("label", "Pool:") in content


def test_withdrawal_view_badges_own_reward_account(seed):
    from seedsigner.views.tx_review.withdrawal_view import WithdrawalReviewView

    parsed = _parsed_tx(seed, _body(seed, withdrawal=True), extra_paths=[PATH_STAKE])
    content = _run_section_view(WithdrawalReviewView, parsed, "withdrawal")["content"]
    assert ("verified", "Own Reward Account") in content


def test_withdrawal_view_unknown_without_stake_path(seed):
    from seedsigner.views.tx_review.withdrawal_view import WithdrawalReviewView

    parsed = _parsed_tx(seed, _body(seed, withdrawal=True))
    content = _run_section_view(WithdrawalReviewView, parsed, "withdrawal")["content"]
    assert ("foreign", "Unknown Reward Account") in content
    assert ("verified", "Own Reward Account") not in content


def test_withdrawal_view_unknown_on_network_mismatch(seed):
    from seedsigner.views.tx_review.withdrawal_view import WithdrawalReviewView

    parsed = _parsed_tx(seed, _body(seed, mainnet_withdrawal=True),
                        extra_paths=[PATH_STAKE])
    content = _run_section_view(WithdrawalReviewView, parsed, "withdrawal")["content"]
    assert ("foreign", "Unknown Reward Account") in content
    assert ("verified", "Own Reward Account") not in content


def test_required_signer_view_badges_own_and_unknown(seed):
    from seedsigner.views.tx_review.required_signer_view import RequiredSignerReviewView

    parsed = _parsed_tx(
        seed,
        _body(seed, required_signers=[_key_hash(seed, PATH_PAYMENT), FOREIGN_KEY_HASH]),
    )
    own = _run_section_view_at(RequiredSignerReviewView, parsed, "required_signer", 0)
    unknown = _run_section_view_at(RequiredSignerReviewView, parsed, "required_signer", 1)
    assert own["badge_text"] == "Own Key" and own["badge_own"] is True
    assert unknown["badge_text"] == "Unknown Key" and unknown["badge_own"] is False


def test_voting_view_badges_own_drep_voter(seed):
    from seedsigner.views.tx_review.voting_view import VotingReviewView

    parsed = _parsed_tx(seed, _body(seed, vote=True), extra_paths=[PATH_DREP])
    content = _run_section_view(VotingReviewView, parsed, "voting")["content"]
    assert ("verified", "Own Key") in content


def test_voting_view_unknown_without_drep_path(seed):
    from seedsigner.views.tx_review.voting_view import VotingReviewView

    parsed = _parsed_tx(seed, _body(seed, vote=True))
    content = _run_section_view(VotingReviewView, parsed, "voting")["content"]
    assert ("foreign", "Unknown Key") in content
    assert ("verified", "Own Key") not in content


def _run_section_view_at(view_cls, parsed_tx, section, item_index):
    """Run the section view for `section`'s item_index-th page with the screen
    mocked; returns the kwargs the view passed to run_screen()."""
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
        assert len(indices) > item_index, f"no page {item_index} for section {section}"
        view.global_index = indices[item_index]
        view.run()

    return captured

"""
Tests that the unified credential explorer base derives the expected first
payment address, stake address and DRep ID for the known mnemonic.

Each concrete explorer differs only in ``_derive_item``; these assert that the
per-item derivation (fed the shared ``root_key_from_seed`` root key, the single
derivation source) yields the canonical values.
"""

from base import BaseTest  # noqa: F401  installs hardware module mocks

from seedsigner.helpers.cardano_utils import root_key_from_seed
from seedsigner.models.seed import Seed
from seedsigner.views.cardano_explorer_views import (
    CardanoPaymentAddressExplorerView,
    CardanoStakeAddressView,
    CardanoDRepIdView,
)


MAINNET = 1

EXPECTED_PAYMENT = "addr1qy8ac7qqy0vtulyl7wntmsxc6wex80gvcyjy33qffrhm7sh927ysx5sftuw0dlft05dz3c7revpf7jx0xnlcjz3g69mq4afdhv"
EXPECTED_STAKE = "stake1u8j40zgr2gy4788kl54h6x3gu0pukq5lfr8nflufpg5dzaskqlx2l"
EXPECTED_DREP = "drep1y2e20afmrjh8wz02w92880qwdqephacyqlahqyp5n6rgnhg2egjc8"


def _seed():
    return Seed(mnemonic=("abandon " * 11 + "about").split())


def _derive_first(view_cls):
    view = object.__new__(view_cls)
    view.account_index = 0
    view.network_id = MAINNET
    return view._derive_item(root_key_from_seed(_seed()), 0)


def test_payment_explorer_first_address():
    assert _derive_first(CardanoPaymentAddressExplorerView) == EXPECTED_PAYMENT


def test_stake_explorer_first_address():
    assert _derive_first(CardanoStakeAddressView) == EXPECTED_STAKE


def test_drep_explorer_first_id():
    assert _derive_first(CardanoDRepIdView) == EXPECTED_DREP

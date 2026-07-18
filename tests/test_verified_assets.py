"""
Tests for the curated verified-asset list and its amount formatting.

A verified asset must only resolve on the network its entry belongs to: a
policy ID is just a script hash, so the same subject can exist on both
mainnet and a testnet with unrelated tokens behind it. The data itself must
stay well-formed (real hex, unique tickers per network, sane decimals) so a
hand-added entry can't silently corrupt the review display.
"""

import base  # noqa: F401  (mocks the Raspi hardware modules before seedsigner imports)

from cometa import NetworkId

from seedsigner.models.verified_assets import (
    MAINNET_ASSETS,
    TESTNET_ASSETS,
    format_asset_amount,
    get_verified_asset,
)


class _Bytes:
    def __init__(self, raw: bytes):
        self._raw = raw

    def to_bytes(self) -> bytes:
        return self._raw


SNEK_POLICY = _Bytes(bytes.fromhex(
    "279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f"))
SNEK_NAME = _Bytes(b"SNEK")


def test_lookup_hit_on_mainnet():
    asset = get_verified_asset(NetworkId.MAINNET, SNEK_POLICY, SNEK_NAME)
    assert asset is not None
    assert asset.ticker == "SNEK"
    assert asset.decimals == 0


def test_mainnet_entry_never_matches_on_testnet():
    assert get_verified_asset(NetworkId.TESTNET, SNEK_POLICY, SNEK_NAME) is None


def test_lookup_miss_for_unknown_asset():
    unknown_policy = _Bytes(b"\x00" * 28)
    assert get_verified_asset(NetworkId.MAINNET, unknown_policy, SNEK_NAME) is None


def test_lookup_miss_for_wrong_asset_name_under_verified_policy():
    assert get_verified_asset(NetworkId.MAINNET, SNEK_POLICY, _Bytes(b"SNEK2")) is None


def test_lookup_hit_for_empty_asset_name():
    oada_policy = _Bytes(bytes.fromhex(
        "f6099832f9563e4cf59602b3351c3c5a8a7dda2d44575ef69b82cf8d"))
    asset = get_verified_asset(NetworkId.MAINNET, oada_policy, _Bytes(b""))
    assert asset is not None
    assert asset.ticker == "OADA"


def test_format_asset_amount():
    assert format_asset_amount(1234567, 6) == "1.234567"
    assert format_asset_amount(1000000, 6) == "1"
    assert format_asset_amount(1500000, 6) == "1.5"
    assert format_asset_amount(0, 6) == "0"
    assert format_asset_amount(-2500000, 6) == "-2.5"
    assert format_asset_amount(123, 0) == "123"
    assert format_asset_amount(1234567890123, 6) == "1,234,567.890123"
    assert format_asset_amount(1, 9) == "0.000000001"


def test_curated_entries_are_well_formed():
    for network_table in (MAINNET_ASSETS, TESTNET_ASSETS):
        tickers = set()
        for (policy_hex, asset_hex), asset in network_table.items():
            policy = bytes.fromhex(policy_hex)
            assert len(policy) == 28
            assert policy_hex == policy.hex()
            name = bytes.fromhex(asset_hex)
            assert len(name) <= 32
            assert asset_hex == name.hex()
            assert asset.ticker
            assert asset.name
            assert 0 <= asset.decimals <= 19
            assert asset.ticker not in tickers
            tickers.add(asset.ticker)

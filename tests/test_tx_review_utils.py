"""
Tests for the transaction review formatting helpers.

format_ada must render lovelace amounts exactly. Cardano's max supply
(45 billion ADA = 4.5e16 lovelace) exceeds the 2^53 integer range of binary
floats, so the conversion must use integer arithmetic or the final digits of
large amounts render incorrectly on the review screens.
"""

import base  # noqa: F401  (mocks the Raspi hardware modules before seedsigner imports)

from seedsigner.gui.screens.tx_review.utils import format_ada, wrap_highlighted_line


def test_format_ada_zero():
    assert format_ada(0) == "0 ADA"


def test_format_ada_single_lovelace():
    assert format_ada(1) == "0.000001 ADA"


def test_format_ada_sub_ada_trailing_zeros_trimmed():
    assert format_ada(10) == "0.00001 ADA"
    assert format_ada(170_000) == "0.17 ADA"
    assert format_ada(999_999) == "0.999999 ADA"


def test_format_ada_whole_ada_has_no_fraction():
    assert format_ada(1_000_000) == "1 ADA"
    assert format_ada(2_000_000) == "2 ADA"
    assert format_ada(1_000_000_000_000) == "1,000,000 ADA"


def test_format_ada_typical_fee():
    assert format_ada(1_500_000) == "1.5 ADA"
    assert format_ada(123_456_789) == "123.456789 ADA"


def test_format_ada_max_supply():
    assert format_ada(45_000_000_000_000_000) == "45,000,000,000 ADA"


def test_format_ada_max_supply_plus_one_lovelace_is_exact():
    assert format_ada(45_000_000_000_000_001) == "45,000,000,000.000001 ADA"


def test_format_ada_large_value_keeps_every_digit():
    assert format_ada(12_345_678_901_234_567) == "12,345,678,901.234567 ADA"


def test_format_ada_negative():
    assert format_ada(-1) == "-0.000001 ADA"
    assert format_ada(-1_500_000) == "-1.5 ADA"


def test_wrap_highlighted_line_line_count_and_chunks():
    display = "a" * 64
    wrapped = wrap_highlighted_line(display, 16)
    assert len(wrapped) == 4
    assert [chunk for _, chunk in wrapped] == ["a" * 16] * 4
    assert [gpos for gpos, _ in wrapped] == [0, 16, 32, 48]


def test_wrap_highlighted_line_last_chunk_shorter():
    display = "a" * 70
    wrapped = wrap_highlighted_line(display, 16)
    assert len(wrapped) == 5
    assert wrapped[-1] == (64, "a" * 6)


def test_wrap_highlighted_line_skips_boundary_space():
    display = "abcd efghij"
    wrapped = wrap_highlighted_line(display, 4)
    assert wrapped == [(0, "abcd"), (5, "efgh"), (9, "ij")]


def test_wrap_highlighted_line_keeps_boundary_space_when_disabled():
    display = "abcd efghij"
    wrapped = wrap_highlighted_line(display, 4, skip_boundary_space=False)
    assert wrapped == [(0, "abcd"), (4, " efg"), (8, "hij")]

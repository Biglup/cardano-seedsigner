"""
Line-type protocol tests for CardanoContentSequentialScreen.

The screen accepts pre-built content lines built by the ``Line``
constructors. An unknown or misspelled line type must be a hard error at
construction rather than a line the renderer silently ignores.
"""

import base  # noqa: F401  (mocks the Raspi hardware modules before seedsigner imports)

import pytest


def test_unknown_line_type_raises():
    from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

    with pytest.raises(ValueError):
        CardanoContentSequentialScreen(content=[("not_a_real_type", "x")])


def test_line_constructors_build_expected_tuples():
    from seedsigner.gui.screens.tx_review import Line

    assert Line.label("Type:") == ("label", "Type:")
    assert Line.spacer() == ("spacer", "")
    assert Line.spacer_small() == ("spacer_small", "")
    assert Line.hash("abc def ghi", 8, 6) == ("hash_display", "abc def ghi", 8, 6)
    assert Line.hero_fields([("F", None, "0")]) == ("hero_fields", [("F", None, "0")])

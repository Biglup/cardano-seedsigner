"""Guards that keep the single version source from drifting.

``seedsigner.__version__`` is the one place the version is declared. The device
display and the packaging metadata both derive from it, so these checks fail if
a second, hardcoded version is reintroduced.
"""

import re
from pathlib import Path

import base  # noqa: F401 (mocks the Raspi hardware modules before seedsigner imports)

from seedsigner import __version__
from seedsigner.controller import Controller


PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+([.-].+)?", __version__)


def test_controller_version_matches_package():
    assert Controller.VERSION == __version__


def test_pyproject_derives_version_from_package():
    text = PYPROJECT.read_text()
    assert 'dynamic = ["version"]' in text
    assert 'version = {attr = "seedsigner.__version__"}' in text
    assert not re.search(r'^version\s*=\s*"', text, re.MULTILINE)

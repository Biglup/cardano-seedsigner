"""
Shared utilities for Cardano transaction review screens.

RET_CODE__LEFT_BUTTON and RET_CODE__RIGHT_BUTTON are the return codes for
sequential left/right navigation.
"""

from gettext import gettext as _


RET_CODE__LEFT_BUTTON = -2
RET_CODE__RIGHT_BUTTON = -3


def format_ada(lovelace: int) -> str:
    """Format a lovelace amount as an exact ADA string using integer arithmetic."""
    sign = "-" if lovelace < 0 else ""
    whole, fraction = divmod(abs(lovelace), 1_000_000)
    formatted = f"{whole:,}"
    decimals = f"{fraction:06d}".rstrip('0')
    if decimals:
        formatted = f"{formatted}.{decimals}"
    return f"{sign}{formatted} ADA"

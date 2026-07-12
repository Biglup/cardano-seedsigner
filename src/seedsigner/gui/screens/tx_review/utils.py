"""
Shared utilities for Cardano transaction review screens.
"""

from gettext import gettext as _


# Return codes for sequential navigation
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


def truncate_address(address: str, max_chars: int = 20) -> str:
    """Truncate a Cardano address for display."""
    if len(address) <= max_chars:
        return address
    half = (max_chars - 3) // 2
    return f"{address[:half]}...{address[-half:]}"


def calc_bezier_curve(p0, p1, p2, num_steps):
    """Calculate a quadratic bezier curve."""
    points = []
    for i in range(num_steps + 1):
        t = i / num_steps
        x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
        y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
        points.append((int(x), int(y)))
    return points


def linear_interp(p0, p1, t):
    """Linear interpolation between two points."""
    return (
        int(p0[0] * (1-t) + p1[0] * t),
        int(p0[1] * (1-t) + p1[1] * t)
    )

"""Collateral return output section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class CollateralReturnReviewView(BaseSequentialSectionView):
    section_title = "Collateral Return"

    def render(self, page, title, has_left, has_right, total_pages):
        output = page.data
        addr_str = str(output.address)
        content_lines = [
            "### Collateral Return",
            f"**{format_ada(output.value.coin)}",
            f"Address:",
            f"  {addr_str[:24]}...",
            f"  ...{addr_str[-16:]}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

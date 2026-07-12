"""Total collateral section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class TotalCollateralReviewView(BaseSequentialSectionView):
    """Review page for the total collateral amount (Conway CDDL body key 17), in ADA."""
    section_title = "Total Collateral"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = [
            f"^^{format_ada(page.data)}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

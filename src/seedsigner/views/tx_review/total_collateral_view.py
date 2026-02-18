"""Total collateral section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class TotalCollateralReviewView(BaseSequentialSectionView):
    section_title = "Total Collateral"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = [
            "### Total Collateral",
            f"**{format_ada(page.data)}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

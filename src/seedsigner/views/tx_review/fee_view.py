"""Fee section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class FeeReviewView(BaseSequentialSectionView):
    section_title = "Fee"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = [
            "### Fee",
            f"**{format_ada(page.data)}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

"""Fee section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class FeeReviewView(BaseSequentialSectionView):
    """Review page for the transaction fee (Conway CDDL body key 2), shown in ADA."""
    section_title = "Fee"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = [
            f"^^{format_ada(page.data)}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

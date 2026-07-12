"""Donation section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class DonationReviewView(BaseSequentialSectionView):
    """Review page for a treasury donation (Conway CDDL body key 22), in ADA."""
    section_title = "Donation"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = [
            f"^^{format_ada(page.data)}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

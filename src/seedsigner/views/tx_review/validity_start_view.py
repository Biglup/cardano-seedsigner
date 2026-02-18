"""Validity interval start section review view."""

from .base import BaseSequentialSectionView


class ValidityStartReviewView(BaseSequentialSectionView):
    section_title = "Valid From"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = [
            "### Valid From",
            f"Slot: {page.data:,}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

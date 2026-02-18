"""TTL (invalid after) section review view."""

from .base import BaseSequentialSectionView


class TtlReviewView(BaseSequentialSectionView):
    section_title = "Invalid After"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = [
            f"^^Slot {page.data:,}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

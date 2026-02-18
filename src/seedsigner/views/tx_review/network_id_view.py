"""Network ID section review view."""

from .base import BaseSequentialSectionView


class NetworkIdReviewView(BaseSequentialSectionView):
    section_title = "Network ID"

    def render(self, page, title, has_left, has_right, total_pages):
        network_id = page.data
        content_lines = [
            "### Network ID",
            f"**{network_id.name} ({network_id.value})",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

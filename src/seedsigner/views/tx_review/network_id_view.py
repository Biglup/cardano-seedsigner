"""Network ID section review view."""

from .base import BaseSequentialSectionView


class NetworkIdReviewView(BaseSequentialSectionView):
    section_title = "Network"

    def render(self, page, title, has_left, has_right, total_pages):
        network_id = page.data
        label = "MAINNET" if network_id.value == 1 else "TESTNET"
        content_lines = [
            f"^^{label}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

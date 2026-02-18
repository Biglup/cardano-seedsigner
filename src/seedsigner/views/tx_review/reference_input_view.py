"""Reference input section review view."""

from .base import BaseSequentialSectionView


class ReferenceInputReviewView(BaseSequentialSectionView):
    section_title = "Ref Input"

    def render(self, page, title, has_left, has_right, total_pages):
        inp = page.data
        tx_id = str(inp.transaction_id)
        content_lines = [
            "### Input",
            f"TX Hash:",
            f"  {tx_id[:24]}...",
            f"  ...{tx_id[-16:]}",
            f"Index: {inp.index}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

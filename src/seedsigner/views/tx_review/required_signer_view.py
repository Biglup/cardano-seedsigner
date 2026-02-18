"""Required signer section review view."""

from .base import BaseSequentialSectionView


class RequiredSignerReviewView(BaseSequentialSectionView):
    section_title = "Required Signer"

    def render(self, page, title, has_left, has_right, total_pages):
        s = str(page.data)
        content_lines = [
            "### Required Signer",
            f"  {s[:32]}",
            f"  {s[32:]}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

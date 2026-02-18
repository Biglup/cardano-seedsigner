"""Script data hash section review view."""

from .base import BaseSequentialSectionView


class ScriptDataHashReviewView(BaseSequentialSectionView):
    section_title = "Script Data Hash"

    def render(self, page, title, has_left, has_right, total_pages):
        h = str(page.data)
        content_lines = [
            "### Script Data Hash",
            f"  {h[:32]}",
            f"  {h[32:]}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

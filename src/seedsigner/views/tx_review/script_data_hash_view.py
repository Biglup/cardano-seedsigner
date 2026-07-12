"""Script data hash section review view."""

from .base import BaseSequentialSectionView


class ScriptDataHashReviewView(BaseSequentialSectionView):
    """Review page for the script data hash (Conway CDDL body key 11)."""
    section_title = "Script Data Hash"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoAuxDataHashScreen

        return self.run_screen(
            CardanoAuxDataHashScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            hash_hex=str(page.data),
        )

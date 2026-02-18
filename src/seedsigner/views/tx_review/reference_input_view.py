"""Reference input section review view."""

from .base import BaseSequentialSectionView


class ReferenceInputReviewView(BaseSequentialSectionView):
    section_title = "Ref Input"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoAuxDataHashScreen

        inp = page.data
        tx_id = inp.transaction_id.hex() if isinstance(inp.transaction_id, bytes) else inp.transaction_id.to_hex()
        utxo_ref = f"{tx_id}#{inp.index}"

        return self.run_screen(
            CardanoAuxDataHashScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            hash_hex=utxo_ref,
        )

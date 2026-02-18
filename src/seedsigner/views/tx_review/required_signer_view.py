"""Required signer section review view."""

from cometa import Bech32

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class RequiredSignerReviewView(BaseSequentialSectionView):
    section_title = "Required Signer"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoAuxDataHashScreen

        signer = page.data
        signer_bytes = signer if isinstance(signer, bytes) else signer.to_bytes()
        bech32_str = Bech32.encode("req_signer_vkh", signer_bytes)
        _, hn, tn = _format_bech32(bech32_str)

        return self.run_screen(
            CardanoAuxDataHashScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            hash_hex=bech32_str,
            head_n=hn,
            tail_n=tn,
        )

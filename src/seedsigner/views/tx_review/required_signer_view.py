"""Required signer section review view."""

from cometa import Bech32

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class RequiredSignerReviewView(BaseSequentialSectionView):
    """Review page for a required signer key hash (Conway CDDL body key 14).

    Badges the signer as an Own Key when its hash is among the key hashes
    derived on-device from the request's declared paths.
    """
    section_title = "Required Signer"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoAuxDataHashScreen

        signer = page.data
        signer_bytes = signer if isinstance(signer, bytes) else signer.to_bytes()
        bech32_str = Bech32.encode("req_signer_vkh", signer_bytes)
        _, hn, tn = _format_bech32(bech32_str)
        is_own = signer_bytes in self.parsed_tx.owned_key_hashes

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
            badge_text="Own Key" if is_own else "Unknown Key",
            badge_own=is_own,
        )

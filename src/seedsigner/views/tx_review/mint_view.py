"""Mint/burn section review view."""

from seedsigner.gui.screens.tx_review import Line
from seedsigner.helpers.cardano_utils import asset_fingerprint

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class MintReviewView(BaseSequentialSectionView):
    """Review page for one policy's mint or burn of native assets (Conway CDDL body key 9)."""
    section_title = "Mint"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

        policy_id, asset_map = page.data
        content = []

        for asset_name, qty in asset_map.items():
            if content:
                content.append(Line.spacer())

            if qty < 0:
                content.append(Line.value_highlight_warn("Burn"))
            elif qty == 0:
                content.append(Line.value_highlight("Mint"))
            else:
                content.append(Line.value_highlight_yes("Mint"))

            content.append(Line.spacer_small())
            fingerprint = asset_fingerprint(policy_id, asset_name)
            fmt, hn, tn = _format_bech32(fingerprint)
            content.append(Line.hash(fmt, hn, tn))

            content.append(Line.spacer_small())
            if qty < 0:
                content.append(Line.value_large_warn(f"{qty:,}"))
            elif qty == 0:
                content.append(Line.value_large("0"))
            else:
                content.append(Line.value_large_yes(f"+{qty:,}"))

        return self.run_screen(
            CardanoContentSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

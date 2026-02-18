"""Mint/burn section review view."""

from .base import BaseSequentialSectionView
from .output_view import _asset_fingerprint
from .certificate_view import _format_bech32


class MintReviewView(BaseSequentialSectionView):
    section_title = "Mint"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen

        policy_id, asset_map = page.data
        content = []

        for asset_name, qty in asset_map.items():
            if content:
                content.append(("spacer", ""))

            is_burn = qty < 0

            # Mint or Burn label
            if is_burn:
                content.append(("value_highlight_warn", "Burn"))
            else:
                content.append(("value_highlight", "Mint"))

            # Asset fingerprint
            content.append(("spacer_small", ""))
            fingerprint = _asset_fingerprint(policy_id, asset_name)
            fmt, hn, tn = _format_bech32(fingerprint)
            content.append(("hash_display", fmt, hn, tn))

            # Quantity
            content.append(("spacer_small", ""))
            sign = "+" if qty > 0 else ""
            if is_burn:
                content.append(("value_large_warn", f"{sign}{qty:,}"))
            else:
                content.append(("value_large", f"+{qty:,}"))

        return self.run_screen(
            CardanoCertificateSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

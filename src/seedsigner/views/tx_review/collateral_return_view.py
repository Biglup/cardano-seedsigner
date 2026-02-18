"""Collateral return output section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class CollateralReturnReviewView(BaseSequentialSectionView):
    section_title = "Collateral Return"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen

        output = page.data
        addr_str = str(output.address)
        fmt, hn, tn = _format_bech32(addr_str)

        content = [
            ("label", "Amount:"),
            ("spacer_small", ""),
            ("value_large", format_ada(output.value.coin)),
            ("spacer", ""),
            ("label", "Address:"),
            ("spacer_small", ""),
            ("hash_display", fmt, hn, tn),
        ]

        return self.run_screen(
            CardanoCertificateSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

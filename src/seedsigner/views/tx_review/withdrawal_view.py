"""Withdrawal section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class WithdrawalReviewView(BaseSequentialSectionView):
    section_title = "Withdrawal"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen

        reward_addr, amount = page.data
        addr_str = str(reward_addr)
        fmt, hn, tn = _format_bech32(addr_str)

        content = [
            ("label", "Amount:"),
            ("spacer_small", ""),
            ("value_large", format_ada(amount)),
            ("spacer", ""),
            ("label", "Reward Account:"),
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

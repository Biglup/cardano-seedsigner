"""Withdrawal section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class WithdrawalReviewView(BaseSequentialSectionView):
    section_title = "Withdrawal"

    def render(self, page, title, has_left, has_right, total_pages):
        reward_addr, amount = page.data
        addr_str = str(reward_addr)
        content_lines = [
            "### Withdrawal",
            f"**{format_ada(amount)}",
            f"Address:",
            f"  {addr_str[:24]}...",
            f"  ...{addr_str[-16:]}",
        ]
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

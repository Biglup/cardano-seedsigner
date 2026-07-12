"""Collateral return output section review view."""

from gettext import gettext as _

from seedsigner.gui.screens.tx_review import format_ada, Line

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class CollateralReturnReviewView(BaseSequentialSectionView):
    section_title = "Collateral Return"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

        output = page.data
        addr_str = str(output.address)
        fmt, hn, tn = _format_bech32(addr_str)
        is_own = self.parsed_tx.collateral_return_verified

        content = [
            Line.label("Amount:"),
            Line.spacer_small(),
            Line.value_large(format_ada(output.value.coin)),
            Line.spacer(),
            (Line.label_own("Address (Own):") if is_own
             else Line.label_foreign("Address (Foreign):")),
            Line.spacer_small(),
            Line.hash(fmt, hn, tn),
        ]
        if is_own:
            content.append(Line.spacer_small())
            content.append(Line.verified(_("Verified Address")))

        return self.run_screen(
            CardanoContentSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

"""Mint/burn section review view."""

from seedsigner.gui.screens.tx_review import Line
from seedsigner.helpers.cardano_utils import asset_fingerprint
from seedsigner.models.verified_assets import format_asset_amount, get_verified_asset

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class MintReviewView(BaseSequentialSectionView):
    """Review page for one policy's mint or burn of native assets (Conway CDDL body key 9).

    An asset on the curated verified list shows its ticker, its amount
    scaled by the attested decimals, and a Verified badge; any other asset
    shows the raw integer amount.
    """
    section_title = "Mint"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

        policy_id, asset_map = page.data
        network = self.parsed_tx.network
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

            verified = get_verified_asset(network, policy_id, asset_name)
            if verified:
                content.append(Line.spacer_small())
                content.append(Line.value_highlight(verified.ticker))

            content.append(Line.spacer_small())
            fingerprint = asset_fingerprint(policy_id, asset_name)
            fmt, hn, tn = _format_bech32(fingerprint)
            content.append(Line.hash(fmt, hn, tn))

            content.append(Line.spacer_small())
            if verified:
                amount = format_asset_amount(qty, verified.decimals)
            else:
                amount = f"{qty:,}"
            if qty < 0:
                content.append(Line.value_large_warn(amount))
            elif qty == 0:
                content.append(Line.value_large("0"))
            else:
                content.append(Line.value_large_yes(f"+{amount}"))
            if verified:
                content.append(Line.verified("Verified"))

        return self.run_screen(
            CardanoContentSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

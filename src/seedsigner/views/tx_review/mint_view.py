"""Mint/burn section review view."""

from .base import BaseSequentialSectionView


class MintReviewView(BaseSequentialSectionView):
    section_title = "Mint/Burn"

    def render(self, page, title, has_left, has_right, total_pages):
        policy_id, asset_map = page.data
        pid_str = str(policy_id)
        content_lines = [
            "### Mint/Burn",
            f"Policy:",
            f"  {pid_str[:24]}...",
        ]
        for asset_name, qty in asset_map.items():
            name_str = str(asset_name) if str(asset_name) else "(empty)"
            sign = "+" if qty > 0 else ""
            content_lines.append(f"**{name_str}: {sign}{qty:,}")
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

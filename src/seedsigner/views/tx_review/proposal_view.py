"""Governance proposal section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class ProposalReviewView(BaseSequentialSectionView):
    section_title = "Proposal"

    def render(self, page, title, has_left, has_right, total_pages):
        proposal = page.data
        content_lines = [
            f"### {proposal.action_type.name}",
            f"**Deposit: {format_ada(proposal.deposit)}",
        ]
        if proposal.anchor:
            content_lines.append(f"Anchor:")
            content_lines.append(f"  {proposal.anchor.url}")
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

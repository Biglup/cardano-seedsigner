"""Voting procedure section review view."""

from .base import BaseSequentialSectionView


class VotingReviewView(BaseSequentialSectionView):
    section_title = "Vote"

    def render(self, page, title, has_left, has_right, total_pages):
        voter, action_id, proc = page.data
        content_lines = [
            f"### {voter.voter_type.name}",
            f"Action:",
            f"  {action_id.hash_hex[:20]}...",
            f"  Index: {action_id.index}",
            f"**Vote: {proc.vote.name}",
        ]
        if proc.anchor:
            content_lines.append(f"Anchor: {proc.anchor.url}")
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

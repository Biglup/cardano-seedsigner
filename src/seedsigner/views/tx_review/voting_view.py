"""Voting procedure section review view."""

from cometa import Bech32, VoterType

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32, _add_anchor


# Voter type -> (friendly name, bech32 prefix)
_VOTER_INFO = {
    VoterType.CONSTITUTIONAL_COMMITTEE_KEY_HASH: ("CC Member", "cc_hot_vkh"),
    VoterType.CONSTITUTIONAL_COMMITTEE_SCRIPT_HASH: ("CC Script", "cc_hot"),
    VoterType.DREP_KEY_HASH: ("DRep", "drep"),
    VoterType.DREP_SCRIPT_HASH: ("DRep Script", "drep_script"),
    VoterType.STAKE_POOL_KEY_HASH: ("SPO", "pool"),
}

# Vote value -> (display text, line type)
_VOTE_DISPLAY = {
    "YES": ("Yes", "value_highlight_yes"),
    "NO": ("No", "value_highlight_no"),
    "ABSTAIN": ("Abstain", "value_highlight"),
}


class VotingReviewView(BaseSequentialSectionView):
    section_title = "Vote"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen

        voter, action_id, proc = page.data
        content = []

        # Vote
        vote_name = proc.vote.name
        display_text, line_type = _VOTE_DISPLAY.get(vote_name, (vote_name, "value_highlight"))
        content.append(("label", "Vote:"))
        content.append(("spacer_small", ""))
        content.append((line_type, display_text))

        # Voter
        content.append(("spacer", ""))
        vt = voter.voter_type
        friendly, prefix = _VOTER_INFO.get(vt, (vt.name, "addr_vkh"))
        bech32_str = Bech32.encode(prefix, voter.credential.hash_bytes)
        fmt, hn, tn = _format_bech32(bech32_str)

        content.append(("label", f"Voter ({friendly}):"))
        content.append(("spacer_small", ""))
        content.append(("hash_display", fmt, hn, tn))

        # Gov Action
        content.append(("spacer", ""))
        gov_bech32 = action_id.to_bech32()
        gov_fmt, gov_hn, gov_tn = _format_bech32(gov_bech32)
        content.append(("label", "Gov Action:"))
        content.append(("spacer_small", ""))
        content.append(("hash_display", gov_fmt, gov_hn, gov_tn))

        if proc.anchor:
            _add_anchor(content, proc.anchor)

        return self.run_screen(
            CardanoCertificateSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

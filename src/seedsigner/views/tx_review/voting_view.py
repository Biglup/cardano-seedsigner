"""Voting procedure section review view.

``_VOTER_INFO`` maps a cometa VoterType to a (friendly name, bech32 prefix)
pair; ``_VOTE_DISPLAY`` maps a vote value name to a (display text, Line
constructor) pair.
"""

from cometa import Bech32, VoterType

from seedsigner.gui.screens.tx_review import Line

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32, _add_anchor


_VOTER_INFO = {
    VoterType.CONSTITUTIONAL_COMMITTEE_KEY_HASH: ("CC Member", "cc_hot_vkh"),
    VoterType.CONSTITUTIONAL_COMMITTEE_SCRIPT_HASH: ("CC Script", "cc_hot"),
    VoterType.DREP_KEY_HASH: ("DRep", "drep"),
    VoterType.DREP_SCRIPT_HASH: ("DRep Script", "drep_script"),
    VoterType.STAKE_POOL_KEY_HASH: ("SPO", "pool"),
}

_VOTE_DISPLAY = {
    "YES": ("Yes", Line.value_highlight_yes),
    "NO": ("No", Line.value_highlight_no),
    "ABSTAIN": ("Abstain", Line.value_highlight),
}


class VotingReviewView(BaseSequentialSectionView):
    """Review page for one governance vote (Conway CDDL body key 19).

    Shows the voter (DRep, committee or SPO credential), the governance action
    voted on, and the Yes/No/Abstain choice, badging an own voter credential.
    """
    section_title = "Vote"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

        voter, action_id, proc = page.data
        content = []

        vote_name = proc.vote.name
        display_text, line_ctor = _VOTE_DISPLAY.get(vote_name, (vote_name, Line.value_highlight))
        content.append(Line.label("Vote:"))
        content.append(Line.spacer_small())
        content.append(line_ctor(display_text))

        content.append(Line.spacer())
        vt = voter.voter_type
        friendly, prefix = _VOTER_INFO.get(vt, (vt.name, "addr_vkh"))
        bech32_str = Bech32.encode(prefix, voter.credential.hash_bytes)
        fmt, hn, tn = _format_bech32(bech32_str)

        content.append(Line.label(f"Voter ({friendly}):"))
        content.append(Line.spacer_small())
        content.append(Line.hash(fmt, hn, tn))
        if voter.credential.is_key_hash:
            is_own = voter.credential.hash_bytes in self.parsed_tx.owned_key_hashes
            content.append(Line.spacer_small())
            content.append(Line.verified("Own Key") if is_own
                           else Line.foreign("Unknown Key"))

        content.append(Line.spacer())
        gov_bech32 = action_id.to_bech32()
        gov_fmt, gov_hn, gov_tn = _format_bech32(gov_bech32)
        content.append(Line.label("Gov Action:"))
        content.append(Line.spacer_small())
        content.append(Line.hash(gov_fmt, gov_hn, gov_tn))

        if proc.anchor:
            _add_anchor(content, proc.anchor)

        return self.run_screen(
            CardanoContentSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

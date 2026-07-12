"""Withdrawal section review view."""

from seedsigner.gui.screens.tx_review import format_ada, Line

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32


class WithdrawalReviewView(BaseSequentialSectionView):
    """Review page for a reward-account withdrawal (Conway CDDL body key 5)."""
    section_title = "Withdrawal"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

        reward_addr, amount = page.data
        addr_str = str(reward_addr)
        fmt, hn, tn = _format_bech32(addr_str)

        content = [
            Line.label("Amount:"),
            Line.spacer_small(),
            Line.value_large(format_ada(amount)),
            Line.spacer(),
            Line.label("Reward Account:"),
            Line.spacer_small(),
            Line.hash(fmt, hn, tn),
        ]
        if self._is_key_hash_account(reward_addr):
            content.append(Line.spacer_small())
            content.append(Line.verified("Own Reward Account")
                           if self._is_own_reward_account(reward_addr)
                           else Line.foreign("Unknown Reward Account"))

        return self.run_screen(
            CardanoContentSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

    def _is_key_hash_account(self, reward_addr) -> bool:
        """Only key-hash reward accounts get an ownership badge; script-hash
        accounts can't be proven either way and stay unbadged (same policy
        as certificate and voter credentials)."""
        try:
            return reward_addr.credential.is_key_hash
        except Exception:
            return False

    def _is_own_reward_account(self, reward_addr) -> bool:
        """A reward account is fully determined by its stake credential and
        network, so an owned key-hash credential on the request's network
        proves the whole address is the wallet's."""
        try:
            cred = reward_addr.credential
            return (
                cred.is_key_hash
                and cred.hash_bytes in self.parsed_tx.owned_key_hashes
                and reward_addr.network_id == self.parsed_tx.network
            )
        except Exception:
            return False

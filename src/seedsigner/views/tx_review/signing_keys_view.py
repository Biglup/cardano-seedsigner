"""Signing-keys inspection step.

A mandatory review page per signing key between the last transaction review
page and the final sign confirmation. The device cannot validate multisig
policy (no UTXO set, no resolved inputs), so this step is where it is honest
about exactly which keys the host is asking it to sign with: each key page
centers the seed fingerprint and the full derivation path.
"""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoParsedTx
from seedsigner.views.view import View, Destination, BackStackView


def build_signing_key_content(seed, path) -> list:
    """Content lines for one signing-key page (shared by the TX and CIP-8
    flows): the seed fingerprint and the derivation path, centered as the
    page's two fields."""
    from seedsigner.helpers.cardano_utils import (
        PURPOSE_MINTING,
        PURPOSE_CIP1854,
        path_purpose,
    )
    from seedsigner.models.cardano_account import format_derivation_path

    purpose = path_purpose(path)
    purpose_tag = {PURPOSE_CIP1854: "(Multisig)", PURPOSE_MINTING: "(Minting)"}.get(purpose)

    return [
        ("hero_fields", [
            ("Fingerprint", None, seed.get_fingerprint()),
            ("Derivation", purpose_tag, format_derivation_path(path)),
        ]),
    ]


class CardanoTxSigningKeysView(View):
    """One page per key this seed will sign with; the sign confirmation is
    only reachable after paging through every key."""

    def __init__(self, parsed_tx: CardanoParsedTx, key_index: int = 0):
        super().__init__()
        self.parsed_tx = parsed_tx
        self.key_index = key_index

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen
        from seedsigner.helpers.cardano_signing import matching_signing_paths
        from .sign_view import CardanoTxSignView

        seed = self.controller.cardano_seed
        request = self.parsed_tx.sign_request

        paths = []
        if seed is not None and request is not None:
            paths = matching_signing_paths(request, seed)
        if not paths:
            return Destination(CardanoTxSignView, view_args=dict(parsed_tx=self.parsed_tx))

        total = len(paths)
        content = build_signing_key_content(seed, paths[self.key_index])

        result = self.run_screen(
            CardanoCertificateSequentialScreen,
            title=f"Signing Key {self.key_index + 1}/{total}" if total > 1 else "Signing Key",
            page_num=self.key_index + 1,
            total_pages=total,
            has_left=True,
            has_right=True,
            content=content,
        )
        return self._handle_navigation(result, total)

    def _handle_navigation(self, result, total):
        from .sign_view import CardanoTxSignView

        if result == RET_CODE__BACK_BUTTON or result == -1:
            return Destination(BackStackView)

        if result == RET_CODE__LEFT_BUTTON:
            if self.key_index > 0:
                return Destination(
                    CardanoTxSigningKeysView,
                    view_args=dict(parsed_tx=self.parsed_tx, key_index=self.key_index - 1),
                    skip_current_view=True,
                )
            return Destination(BackStackView)

        if result == RET_CODE__RIGHT_BUTTON:
            if self.key_index >= total - 1:
                return Destination(CardanoTxSignView, view_args=dict(parsed_tx=self.parsed_tx))
            return Destination(
                CardanoTxSigningKeysView,
                view_args=dict(parsed_tx=self.parsed_tx, key_index=self.key_index + 1),
                skip_current_view=True,
            )

        return Destination(BackStackView)

"""Address display screen for CIP-8 message signing."""

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoMessageSignRequest
from seedsigner.views.view import View, Destination, BackStackView

# Total pages in the message signing flow (address, payload)
_TOTAL_PAGES = 2


class CardanoMsgAddressView(View):
    """Shows the signing address in bech32."""

    def __init__(self, msg_request: CardanoMessageSignRequest, page_index: int = 0):
        super().__init__()
        self.msg_request = msg_request
        self.page_index = page_index

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen
        from seedsigner.views.tx_review.certificate_view import _format_bech32

        content = []

        if self.msg_request.address_bytes:
            label, bech32_str = _decode_address(self.msg_request.address_bytes)
            content.append(("label", label))
            content.append(("spacer_small", ""))
            fmt, hn, tn = _format_bech32(bech32_str)
            content.append(("hash_display", fmt, hn, tn))
        else:
            content.append(("label", "Address:"))
            content.append(("spacer_small", ""))
            content.append(("value_highlight", "(not provided)"))

        result = self.run_screen(
            CardanoCertificateSequentialScreen,
            title="Sign With",
            page_num=1,
            total_pages=_TOTAL_PAGES,
            has_left=True,
            has_right=True,
            content=content,
        )

        return self._handle_navigation(result)

    def _handle_navigation(self, result):
        from .payload_view import CardanoMsgPayloadView

        if result == RET_CODE__BACK_BUTTON or result == -1:
            return Destination(BackStackView)

        if result == RET_CODE__LEFT_BUTTON:
            return Destination(BackStackView)

        if result == RET_CODE__RIGHT_BUTTON:
            return Destination(
                CardanoMsgPayloadView,
                view_args=dict(msg_request=self.msg_request, page_index=1),
                skip_current_view=True,
            )

        return Destination(BackStackView)


def _decode_address(address_bytes):
    """Decode address_bytes to (label, bech32_str).

    Tries standard Cardano address first, falls back to DRep credential
    (28-byte raw key hash).
    """
    from cometa import Address, AddressType

    try:
        addr = Address.from_bytes(address_bytes)
        addr_type = addr.type
        bech32_str = str(addr)

        if addr_type in (AddressType.REWARD_KEY, AddressType.REWARD_SCRIPT):
            return "Stake Address:", bech32_str
        else:
            return "Payment Address:", bech32_str
    except Exception:
        pass

    # 28-byte raw hash → DRep credential
    if len(address_bytes) == 28:
        from cometa import Blake2bHash, Credential, DRep, DRepType
        h = Blake2bHash.from_bytes(address_bytes)
        cred = Credential.from_key_hash(h)
        drep = DRep.new(DRepType.KEY_HASH, cred)
        return "DRep ID:", str(drep)

    return "Address:", address_bytes.hex()

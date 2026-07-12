from gettext import gettext as _

from seedsigner.gui.components import SeedSignerIconConstants
from seedsigner.gui.screens import RET_CODE__BACK_BUTTON, ButtonListScreen
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.models.encode_qr import GenericStaticQrEncoder
from seedsigner.models.settings import SettingsConstants
from seedsigner.views.view import View, Destination, BackStackView


class CardanoAddressExplorerNetworkView(View):
    """Choose network before exploring addresses."""
    MAINNET = ButtonOption("Mainnet", return_data=1)
    TESTNET = ButtonOption("Testnet", return_data=0)

    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        button_data = [self.MAINNET, self.TESTNET]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Select Network"),
            is_button_text_centered=True,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        network_id = button_data[selected_menu_num].return_data

        multi = self.settings.get_value(SettingsConstants.SETTING__MULTI_ACCOUNTS) == SettingsConstants.OPTION__ENABLED
        if multi:
            return Destination(CardanoAccountSelectView, view_args=dict(seed_num=self.seed_num, network_id=network_id))

        return Destination(CardanoAddressExplorerTypeView, view_args=dict(seed_num=self.seed_num, network_id=network_id, account_index=0))



class CardanoAccountSelectView(View):
    """Select which CIP-1852 account index to explore. Paginated like address list.

    Account rows are rendered as derivation path labels (m/1852'/1815'/i')
    on the address list screen; the entry after the last row is the Next
    page button.
    """

    ACCOUNTS_PER_PAGE = 10

    def __init__(self, seed_num: int, network_id: int = 1, start_index: int = 0):
        super().__init__()
        self.seed_num = seed_num
        self.network_id = network_id
        self.start_index = start_index


    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsAddressExplorerAddressListScreen

        addresses = []
        for i in range(self.start_index, self.start_index + self.ACCOUNTS_PER_PAGE):
            addresses.append(f"m/1852'/1815'/{i}'")

        selected_menu_num = self.run_screen(
            ToolsAddressExplorerAddressListScreen,
            title=_("Select Account"),
            start_index=self.start_index,
            addresses=addresses,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == len(addresses):
            return Destination(
                CardanoAccountSelectView,
                view_args=dict(seed_num=self.seed_num, network_id=self.network_id, start_index=self.start_index + self.ACCOUNTS_PER_PAGE),
            )

        account_index = selected_menu_num + self.start_index
        return Destination(CardanoAddressExplorerTypeView, view_args=dict(
            seed_num=self.seed_num, network_id=self.network_id, account_index=account_index,
        ))



class CardanoAddressExplorerTypeView(View):
    """Choose which credential type to explore."""
    PAYMENT = ButtonOption("Payment addresses")
    STAKE = ButtonOption("Stake address")
    DREP = ButtonOption("DRep ID")

    def __init__(self, seed_num: int, network_id: int = 1, account_index: int = 0):
        super().__init__()
        self.seed_num = seed_num
        self.network_id = network_id
        self.account_index = account_index


    def run(self):
        button_data = [self.PAYMENT, self.STAKE, self.DREP]

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Address Explorer"),
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        view_args = dict(seed_num=self.seed_num, network_id=self.network_id, account_index=self.account_index)

        if button_data[selected_menu_num] == self.PAYMENT:
            return Destination(CardanoPaymentAddressExplorerView, view_args=view_args)

        elif button_data[selected_menu_num] == self.STAKE:
            return Destination(CardanoStakeAddressView, view_args=view_args)

        elif button_data[selected_menu_num] == self.DREP:
            return Destination(CardanoDRepIdView, view_args=view_args)



class CardanoExplorerListView(View):
    """Shared pagination and detail routing for the credential explorers.

    Subclasses implement ``_derive_item(root_key, index)`` and the title
    hooks. When ``_single_title`` returns a value and multi credentials are
    disabled, item 0 is shown directly; otherwise a paginated list routes the
    selected entry to ``CardanoAddressDetailView``, and the entry after the
    last item is the Next page button.
    """

    ADDRS_PER_PAGE = 10
    parent_view = None

    def __init__(self, seed_num: int, network_id: int = 1, account_index: int = 0, start_index: int = 0, selected_button_index: int = 0, initial_scroll: int = 0):
        super().__init__()
        self.seed_num = seed_num
        self.network_id = network_id
        self.account_index = account_index
        self.start_index = start_index
        self.selected_button_index = selected_button_index
        self.initial_scroll = initial_scroll
        self.seed = self.controller.get_seed(seed_num)


    def _derive_item(self, root_key, index: int) -> str:
        raise NotImplementedError


    def _list_title(self) -> str:
        raise NotImplementedError


    def _single_title(self):
        return None


    def _detail_title(self, index: int) -> str:
        raise NotImplementedError


    def run(self):
        from seedsigner.helpers.cardano_utils import root_key_from_seed

        root_key = root_key_from_seed(self.seed)

        single_title = self._single_title()
        if single_title is not None:
            multi = self.settings.get_value(SettingsConstants.SETTING__MULTI_CREDENTIALS) == SettingsConstants.OPTION__ENABLED
            if not multi:
                item = self._derive_item(root_key, 0)
                return Destination(
                    CardanoAddressDetailView,
                    view_args=dict(seed_num=self.seed_num, address=item, title=single_title),
                    skip_current_view=True,
                )

        from seedsigner.gui.screens.tools_screens import ToolsAddressExplorerAddressListScreen

        addresses = []
        for i in range(self.start_index, self.start_index + self.ADDRS_PER_PAGE):
            addresses.append(self._derive_item(root_key, i))

        selected_menu_num = self.run_screen(
            ToolsAddressExplorerAddressListScreen,
            title=self._list_title(),
            start_index=self.start_index,
            addresses=addresses,
            selected_button=self.selected_button_index,
            scroll_y_initial_offset=self.initial_scroll,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == len(addresses):
            return Destination(
                type(self),
                view_args=dict(seed_num=self.seed_num, network_id=self.network_id, account_index=self.account_index, start_index=self.start_index + self.ADDRS_PER_PAGE),
            )

        index = selected_menu_num + self.start_index
        initial_scroll = self.screen.buttons[0].scroll_y
        return Destination(
            CardanoAddressDetailView,
            view_args=dict(
                seed_num=self.seed_num,
                network_id=self.network_id,
                account_index=self.account_index,
                address=addresses[selected_menu_num],
                title=self._detail_title(index),
                start_index=self.start_index,
                parent_initial_scroll=initial_scroll,
                parent_selected=selected_menu_num,
                parent_view=self.parent_view,
            ),
            skip_current_view=True,
        )



class CardanoPaymentAddressExplorerView(CardanoExplorerListView):
    """Display Cardano receive addresses, click one to see full address + QR.

    Base addresses combine a per-index payment key
    (m/1852'/1815'/account'/0/index) with the account's staking key
    (m/1852'/1815'/account'/2/0), which is shared across all addresses.
    """

    parent_view = "payment"

    def _stake_credential(self, root_key):
        """Derive the account staking credential (m/1852'/1815'/account'/2/0).

        Shared by every payment address on the page, so it is derived once
        and cached on the view.
        """
        if getattr(self, "_cached_stake_cred", None) is None:
            from cometa import Credential
            from seedsigner.helpers.cardano_utils import (
                HARDENED_OFFSET,
                PURPOSE_CIP1852,
                COIN_TYPE_ADA,
                ROLE_STAKE,
            )
            account = self.account_index | HARDENED_OFFSET
            stake_key = root_key.derive(
                [PURPOSE_CIP1852 | HARDENED_OFFSET, COIN_TYPE_ADA | HARDENED_OFFSET, account, ROLE_STAKE, 0])
            self._cached_stake_cred = Credential.from_key_hash(
                stake_key.get_public_key().to_ed25519_key().to_hash()
            )
        return self._cached_stake_cred

    def _derive_item(self, root_key, index: int) -> str:
        from cometa import BaseAddress, Credential
        from seedsigner.helpers.cardano_utils import (
            HARDENED_OFFSET,
            PURPOSE_CIP1852,
            COIN_TYPE_ADA,
            ROLE_PAYMENT,
        )
        account = self.account_index | HARDENED_OFFSET
        stake_cred = self._stake_credential(root_key)
        payment_key = root_key.derive(
            [PURPOSE_CIP1852 | HARDENED_OFFSET, COIN_TYPE_ADA | HARDENED_OFFSET, account, ROLE_PAYMENT, index])
        payment_cred = Credential.from_key_hash(
            payment_key.get_public_key().to_ed25519_key().to_hash()
        )
        return str(BaseAddress.from_credentials(self.network_id, payment_cred, stake_cred))


    def _list_title(self) -> str:
        return _("Payment Addrs")


    def _detail_title(self, index: int) -> str:
        return _("Address #{}").format(index)



class CardanoStakeAddressView(CardanoExplorerListView):
    """Display staking (reward) addresses.

    Reward addresses use the staking key m/1852'/1815'/account'/2/index.
    With multi credentials disabled, index 0 is shown directly; otherwise
    a paginated list is offered.
    """

    parent_view = "stake"

    def _derive_item(self, root_key, index: int) -> str:
        from cometa import RewardAddress, Credential
        from seedsigner.helpers.cardano_utils import (
            HARDENED_OFFSET,
            PURPOSE_CIP1852,
            COIN_TYPE_ADA,
            ROLE_STAKE,
        )
        account = self.account_index | HARDENED_OFFSET
        stake_key = root_key.derive(
            [PURPOSE_CIP1852 | HARDENED_OFFSET, COIN_TYPE_ADA | HARDENED_OFFSET, account, ROLE_STAKE, index])
        stake_cred = Credential.from_key_hash(
            stake_key.get_public_key().to_ed25519_key().to_hash()
        )
        return str(RewardAddress.from_credentials(self.network_id, stake_cred))


    def _list_title(self) -> str:
        return _("Stake Addrs")


    def _single_title(self):
        return _("Stake Address")


    def _detail_title(self, index: int) -> str:
        return _("Stake #{}").format(index)



class CardanoDRepIdView(CardanoExplorerListView):
    """Display DRep IDs.

    DRep IDs derive from the key m/1852'/1815'/account'/3/index. With
    multi credentials disabled, index 0 is shown directly; otherwise a
    paginated list is offered.
    """

    parent_view = "drep"

    def _derive_item(self, root_key, index: int) -> str:
        from cometa import DRep, DRepType, Credential
        from seedsigner.helpers.cardano_utils import (
            HARDENED_OFFSET,
            PURPOSE_CIP1852,
            COIN_TYPE_ADA,
            ROLE_DREP,
        )
        account = self.account_index | HARDENED_OFFSET
        drep_key = root_key.derive(
            [PURPOSE_CIP1852 | HARDENED_OFFSET, COIN_TYPE_ADA | HARDENED_OFFSET, account, ROLE_DREP, index])
        drep_hash = drep_key.get_public_key().to_ed25519_key().to_hash()
        cred = Credential.from_key_hash(drep_hash)
        drep = DRep.new(DRepType.KEY_HASH, cred)
        return drep.to_cip129_string()


    def _list_title(self) -> str:
        return _("DRep IDs")


    def _single_title(self):
        return _("DRep ID")


    def _detail_title(self, index: int) -> str:
        return _("DRep #{}").format(index)



class CardanoAddressDetailView(View):
    """Show full address text with Back and Show QR buttons.

    Show QR (button 0) displays the address as a static QR and then
    returns to this same detail view.
    """
    SHOW_QR = ButtonOption("Show QR", SeedSignerIconConstants.QRCODE)

    def __init__(self, seed_num: int, address: str, title: str,
                 network_id: int = 1, account_index: int = 0, start_index: int = 0,
                 parent_initial_scroll: int = 0, parent_selected: int = 0, parent_view: str = None):
        super().__init__()
        self.seed_num = seed_num
        self.network_id = network_id
        self.account_index = account_index
        self.address = address
        self.title = title
        self.start_index = start_index
        self.parent_initial_scroll = parent_initial_scroll
        self.parent_selected = parent_selected
        self.parent_view = parent_view


    def run(self):
        from seedsigner.gui.screens.cardano_address_screen import CardanoAddressDetailScreen

        selected_menu_num = self.run_screen(
            CardanoAddressDetailScreen,
            address=self.address,
            address_title=self.title,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            parent_list_views = {
                "payment": CardanoPaymentAddressExplorerView,
                "stake": CardanoStakeAddressView,
                "drep": CardanoDRepIdView,
            }
            if self.parent_view in parent_list_views:
                return Destination(
                    parent_list_views[self.parent_view],
                    view_args=dict(
                        seed_num=self.seed_num,
                        network_id=self.network_id,
                        account_index=self.account_index,
                        start_index=self.start_index,
                        selected_button_index=self.parent_selected,
                        initial_scroll=self.parent_initial_scroll,
                    ),
                    skip_current_view=True,
                )
            return Destination(BackStackView)

        if selected_menu_num == 0:
            from seedsigner.gui.screens.screen import QRDisplayScreen
            qr_encoder = GenericStaticQrEncoder(data=self.address)
            self.run_screen(
                QRDisplayScreen,
                qr_encoder=qr_encoder,
            )
            return Destination(
                CardanoAddressDetailView,
                view_args=dict(
                    seed_num=self.seed_num,
                    network_id=self.network_id,
                    account_index=self.account_index,
                    address=self.address,
                    title=self.title,
                    start_index=self.start_index,
                    parent_initial_scroll=self.parent_initial_scroll,
                    parent_selected=self.parent_selected,
                    parent_view=self.parent_view,
                ),
                skip_current_view=True,
            )

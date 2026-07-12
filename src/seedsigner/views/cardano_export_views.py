import logging

from gettext import gettext as _

from seedsigner.gui.components import FontAwesomeIconConstants, GUIConstants, SeedSignerIconConstants
from seedsigner.gui.screens import RET_CODE__BACK_BUTTON, ButtonListScreen, WarningScreen, seed_screens
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.models.settings import SettingsConstants
from seedsigner.views.view import View, Destination, BackStackView, MainMenuView, ErrorView

logger = logging.getLogger(__name__)


class CardanoExportAccountKeyView(View):
    """Export an account extended public key as a bech32-encoded QR code,
    choosing between an ordinary (CIP-1852) and a multisig (CIP-1854) key."""

    SINGLE_SIG = ButtonOption("Single-sig (CIP-1852)")
    MULTI_SIG = ButtonOption("Multisig (CIP-1854)")

    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num


    def run(self):
        from seedsigner.models.cardano_account import PURPOSE_CIP1852, PURPOSE_CIP1854

        button_data = [self.SINGLE_SIG, self.MULTI_SIG]
        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Export Account Key"),
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        key_purpose = (PURPOSE_CIP1854 if button_data[selected_menu_num] == self.MULTI_SIG
                       else PURPOSE_CIP1852)
        return Destination(
            CardanoExportAccountKeySelectView,
            view_args=dict(seed_num=self.seed_num, key_purpose=key_purpose),
        )



class CardanoExportAccountKeySelectView(View):
    """Paginated account selection for account key export."""

    ACCOUNTS_PER_PAGE = 10

    def __init__(self, seed_num: int, start_index: int = 0, key_purpose: int = None):
        super().__init__()
        from seedsigner.models.cardano_account import PURPOSE_CIP1852
        self.seed_num = seed_num
        self.start_index = start_index
        self.key_purpose = key_purpose if key_purpose is not None else PURPOSE_CIP1852


    def run(self):
        from seedsigner.gui.screens.tools_screens import ToolsAddressExplorerAddressListScreen

        addresses = []
        for i in range(self.start_index, self.start_index + self.ACCOUNTS_PER_PAGE):
            addresses.append(f"m/{self.key_purpose}'/1815'/{i}'")

        selected_menu_num = self.run_screen(
            ToolsAddressExplorerAddressListScreen,
            title=_("Export Account Key"),
            start_index=self.start_index,
            addresses=addresses,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == len(addresses):
            return Destination(
                CardanoExportAccountKeySelectView,
                view_args=dict(seed_num=self.seed_num,
                               start_index=self.start_index + self.ACCOUNTS_PER_PAGE,
                               key_purpose=self.key_purpose),
            )

        account_index = selected_menu_num + self.start_index

        destination = Destination(
            CardanoExportAccountKeyDetailsView,
            view_args={"seed_num": self.seed_num, "account_indices": [account_index],
                       "key_purpose": self.key_purpose},
            skip_current_view=True,
        )

        if self.settings.get_value(SettingsConstants.SETTING__PRIVACY_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            return destination

        selected_menu_num = self.run_screen(
            WarningScreen,
            status_headline=_("Privacy Leak!"),
            text=_("Account key can be used to view all past and future transactions."),
        )

        if selected_menu_num == 0:
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class CardanoSelectSeedView(View):
    """Shared seed-selection step for scan-initiated Cardano flows.

    0 seeds -> offer Scan/Type and set the subclass resume flow; 1 -> auto-
    select; N -> fingerprint picker. Subclasses provide ``_resume_flow`` and
    the destination reached once a seed is chosen (``_seed_selected_destination``).
    """

    SCAN_SEED = ButtonOption("Scan a seed", SeedSignerIconConstants.QRCODE)
    TYPE_12WORD = ButtonOption("Enter 12-word seed", FontAwesomeIconConstants.KEYBOARD)
    TYPE_24WORD = ButtonOption("Enter 24-word seed", FontAwesomeIconConstants.KEYBOARD)


    def run(self):
        from seedsigner.views.seed_views import SeedMnemonicEntryView

        seeds = self.controller.storage.seeds

        if len(seeds) == 1:
            return self._seed_selected_destination(0)

        button_data = []
        for seed in seeds:
            button_data.append(ButtonOption(
                seed.get_fingerprint(),
                SeedSignerIconConstants.FINGERPRINT,
                icon_color=GUIConstants.ACCENT_TEXT_COLOR,
            ))
        button_data.append(self.SCAN_SEED)
        button_data.append(self.TYPE_12WORD)
        button_data.append(self.TYPE_24WORD)

        selected_menu_num = self.run_screen(
            ButtonListScreen,
            title=_("Select Seed"),
            is_button_text_centered=False,
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if len(seeds) > 0 and selected_menu_num < len(seeds):
            return self._seed_selected_destination(selected_menu_num)

        self.controller.resume_main_flow = self._resume_flow()

        if button_data[selected_menu_num] == self.SCAN_SEED:
            from seedsigner.views.scan_views import ScanSeedQRView
            return Destination(ScanSeedQRView)

        elif button_data[selected_menu_num] in [self.TYPE_12WORD, self.TYPE_24WORD]:
            num_words = 12 if button_data[selected_menu_num] == self.TYPE_12WORD else 24
            self.controller.storage.init_pending_mnemonic(num_words=num_words)
            return Destination(SeedMnemonicEntryView)


    def _resume_flow(self):
        raise NotImplementedError


    def _seed_selected_destination(self, seed_num: int):
        raise NotImplementedError


    def _invalid_request_destination(self, text: str):
        return Destination(ErrorView, view_args=dict(
            title="Error",
            status_headline=_("Invalid Request"),
            text=text,
            button_text="Back",
            next_destination=Destination(MainMenuView, clear_history=True),
        ), skip_current_view=True)



class CardanoExportSelectSeedView(CardanoSelectSeedView):
    """Select which loaded seed to export account keys from."""

    def _resume_flow(self):
        from seedsigner.controller import Controller
        return Controller.FLOW__CARDANO_ACCOUNT_EXPORT

    def _seed_selected_destination(self, seed_num: int):
        return Destination(
            CardanoExportAccountKeyConsentView,
            view_args=dict(seed_num=seed_num),
            skip_current_view=True,
        )



class CardanoExportAccountKeyConsentView(View):
    """Enforce the multi-account gate and the privacy warning before export."""

    def __init__(self, seed_num: int):
        super().__init__()
        self.seed_num = seed_num
        self.request = self.controller.cardano_account_request


    def run(self):
        from seedsigner.models.cardano_account import PURPOSE_CIP1852

        account_indices = self.request.account_indices if self.request else [0]
        request_id = self.request.request_id if self.request else ""
        key_purpose = self.request.key_purpose if self.request else PURPOSE_CIP1852

        multi_enabled = self.settings.get_value(SettingsConstants.SETTING__MULTI_ACCOUNTS) == SettingsConstants.OPTION__ENABLED
        needs_multi = len(account_indices) > 1 or any(index != 0 for index in account_indices)
        if needs_multi and not multi_enabled:
            self.run_screen(
                WarningScreen,
                title=_("Multi Accounts"),
                status_headline=_("Not Enabled"),
                text=_("Enable Multi accounts in Settings to export these accounts."),
                show_back_button=False,
                button_data=[ButtonOption("OK")],
            )
            self.controller.cardano_account_request = None
            return Destination(MainMenuView, clear_history=True)

        destination = Destination(
            CardanoExportAccountKeyDetailsView,
            view_args=dict(seed_num=self.seed_num, account_indices=account_indices,
                           request_id=request_id, key_purpose=key_purpose),
            skip_current_view=True,
        )

        if self.settings.get_value(SettingsConstants.SETTING__PRIVACY_WARNINGS) == SettingsConstants.OPTION__DISABLED:
            return destination

        accounts_text = ", ".join(str(index) for index in account_indices)
        selected_menu_num = self.run_screen(
            WarningScreen,
            status_headline=_("Privacy Leak!"),
            text=_("Account key(s) for account {} can view all past and future transactions.").format(accounts_text),
        )

        if selected_menu_num == 0:
            return destination

        elif selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)



class CardanoExportAccountKeyDetailsView(View):
    """Show the fingerprint, derivation path and xpub for confirmation before the QR.

    Host requests may cover multiple accounts; each one gets its own details
    screen (``key_index`` walks ``account_indices``) before the QR is shown.
    """

    def __init__(self, seed_num: int, account_indices: list = None, request_id: str = "",
                 key_index: int = 0, key_purpose: int = None):
        super().__init__()
        from seedsigner.models.cardano_account import PURPOSE_CIP1852
        self.seed_num = seed_num
        self.account_indices = account_indices if account_indices is not None else [0]
        self.request_id = request_id
        self.key_index = key_index
        self.key_purpose = key_purpose if key_purpose is not None else PURPOSE_CIP1852
        self.seed = self.controller.get_seed(seed_num)


    def run(self):
        from cometa import Bech32
        from seedsigner.gui.screens.screen import LoadingScreenThread
        from seedsigner.models.cardano_account import (
            account_xpub_hrp,
            derive_account_keys,
            format_derivation_path,
        )

        account_index = self.account_indices[self.key_index]

        loading_screen = LoadingScreenThread(text=_("Generating xpub..."))
        loading_screen.start()
        try:
            account_key = derive_account_keys(self.seed, [account_index], self.key_purpose)[0]
            fingerprint = self.seed.get_fingerprint()
            derivation_path = format_derivation_path(account_key.path)
            xpub = Bech32.encode(account_xpub_hrp(self.key_purpose), account_key.xpub)
        finally:
            loading_screen.stop()

        selected_menu_num = self.run_screen(
            seed_screens.CardanoExportAccountKeyDetailsScreen,
            fingerprint=fingerprint,
            derivation_path=derivation_path,
            xpub=xpub,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if self.key_index + 1 < len(self.account_indices):
            return Destination(
                CardanoExportAccountKeyDetailsView,
                view_args=dict(
                    seed_num=self.seed_num,
                    account_indices=self.account_indices,
                    request_id=self.request_id,
                    key_index=self.key_index + 1,
                    key_purpose=self.key_purpose,
                ),
            )

        return Destination(
            CardanoExportAccountKeyQRView,
            view_args=dict(seed_num=self.seed_num, account_indices=self.account_indices,
                           request_id=self.request_id, key_purpose=self.key_purpose),
        )



class CardanoExportAccountKeyQRView(View):
    """Display the account extended public key(s) as an animated QR code."""

    def __init__(self, seed_num: int, account_indices: list = None, request_id: str = "",
                 key_purpose: int = None):
        super().__init__()
        from seedsigner.models.cardano_account import PURPOSE_CIP1852, build_account_response
        from seedsigner.models.encode_qr import CardanoAccountQrEncoder

        seed = self.controller.get_seed(seed_num)
        if account_indices is None:
            account_indices = [0]
        if key_purpose is None:
            key_purpose = PURPOSE_CIP1852

        response = build_account_response(seed, request_id, account_indices, key_purpose)
        self.qr_encoder = CardanoAccountQrEncoder(
            response=response,
            qr_density=self.settings.get_value(SettingsConstants.SETTING__QR_DENSITY),
        )


    def run(self):
        from seedsigner.gui.screens.screen import QRDisplayScreen
        self.run_screen(
            QRDisplayScreen,
            qr_encoder=self.qr_encoder,
        )

        self.controller.cardano_account_request = None
        return Destination(MainMenuView)



class CardanoTxSelectSeedView(CardanoSelectSeedView):
    """Select which loaded seed signs a scanned Cardano transaction."""

    def _resume_flow(self):
        from seedsigner.controller import Controller
        return Controller.FLOW__CARDANO_TX_SIGN

    def _seed_selected_destination(self, seed_num: int):
        from seedsigner.gui.screens.screen import LoadingScreenThread

        seed = self.controller.get_seed(seed_num)
        request = self.controller.cardano_tx_sign_request

        loading_screen = LoadingScreenThread(text=_("Loading transaction..."))
        loading_screen.start()
        try:
            from seedsigner.views.tx_review.overview_view import CardanoTxOverviewView
            from seedsigner.models.cardano_tx import CardanoParsedTx

            parsed_tx = CardanoParsedTx.for_seed(request, seed)
        except Exception as e:
            logger.info(repr(e), exc_info=True)
            return self._invalid_request_destination(_("Could not read the transaction to sign."))
        finally:
            loading_screen.stop()

        self.controller.cardano_seed = seed
        return Destination(
            CardanoTxOverviewView,
            view_args=dict(parsed_tx=parsed_tx),
            skip_current_view=True,
        )



class CardanoMsgSelectSeedView(CardanoSelectSeedView):
    """Select which loaded seed signs a scanned CIP-8 message."""

    def _resume_flow(self):
        from seedsigner.controller import Controller
        return Controller.FLOW__CARDANO_CIP8_SIGN

    def _seed_selected_destination(self, seed_num: int):
        from seedsigner.views.msg_sign.overview_view import CardanoMsgOverviewView

        seed = self.controller.get_seed(seed_num)
        request = self.controller.cardano_cip8_sign_request

        try:
            if request is None or request.message_payload is None \
                    or request.required_signing_path is None:
                raise ValueError("incomplete cardano-cip8-sig-req")
        except Exception as e:
            logger.info(repr(e), exc_info=True)
            return self._invalid_request_destination(_("Could not read the message to sign."))

        self.controller.cardano_seed = seed
        return Destination(
            CardanoMsgOverviewView,
            view_args=dict(msg_request=request),
            skip_current_view=True,
        )

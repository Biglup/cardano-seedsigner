import logging

from gettext import gettext as _
from seedsigner.helpers.l10n import mark_for_translation as _mft
from seedsigner.models.settings import SettingsConstants
from seedsigner.views.view import BackStackView, ErrorView, MainMenuView, NotYetImplementedView, View, Destination
from seedsigner.gui.screens.screen import ButtonOption

logger = logging.getLogger(__name__)


def _error_detail(e: Exception) -> str:
    """A short diagnostic line for the error screen.

    Restricted to printable ASCII so a hostile QR payload echoed through an
    exception message can't render arbitrary text on the device.
    """
    raw = f"{type(e).__name__}: {e}"
    return "".join(ch for ch in raw if ch.isprintable() and ord(ch) < 127)[:120]



class ScanView(View):
    """
        The catch-all generic scanning View that will accept any of our supported QR
        formats and will route to the most sensible next step.

        Can also be used as a base class for more specific scanning flows with
        dedicated errors when an unexpected QR type is scanned (e.g. Scan PSBT was
        selected but a SeedQR was scanned).
    """
    instructions_text = _mft("Scan a QR code")
    invalid_qr_type_message = _mft("QRCode not recognized or not yet supported.")


    def __init__(self):
        from seedsigner.models.decode_qr import DecodeQR

        super().__init__()
        # Define the decoder here to make it available to child classes' is_valid_qr_type
        # checks and so we can inject data into it in the test suite's `before_run()`.
        self.wordlist_language_code = self.settings.get_value(SettingsConstants.SETTING__WORDLIST_LANGUAGE)
        self.decoder: DecodeQR = DecodeQR(wordlist_language_code=self.wordlist_language_code)


    @property
    def is_valid_qr_type(self):
        return True


    def run(self):
        from seedsigner.gui.screens.scan_screens import ScanScreen

        # Start the live preview and background QR reading
        self.run_screen(
            ScanScreen,
            instructions_text=self.instructions_text,
            decoder=self.decoder
        )

        # A long scan might have exceeded the screensaver timeout; ensure screensaver
        # doesn't immediately engage when we leave here.
        self.controller.reset_screensaver_timeout()

        # Handle the results
        if self.decoder.is_complete:
            if not self.is_valid_qr_type:
                # We recognized the QR type but it was not the type expected for the
                # current flow.
                # Report QR types in more human-readable text (e.g. QRType
                # `seed__compactseedqr` as "seed: compactseedqr").
                # TODO: cleanup l10n presentation
                return Destination(ErrorView, view_args=dict(
                    title="Error",
                    status_headline=_("Wrong QR Type"),
                    text=_(self.invalid_qr_type_message) + f""", received "{self.decoder.qr_type.replace("__", ": ").replace("_", " ")}\" format""",
                    button_text="Back",
                    next_destination=Destination(BackStackView, skip_current_view=True),
                ))

            if self.decoder.is_seed:
                seed_mnemonic = self.decoder.get_seed_phrase()

                if not seed_mnemonic:
                    # seed is not valid, Exit if not valid with message
                    return Destination(NotYetImplementedView)
                else:
                    # Found a valid mnemonic seed! All new seeds should be considered
                    #   pending (might set a passphrase, SeedXOR, etc) until finalized.
                    from seedsigner.models.seed import Seed
                    from .seed_views import SeedFinalizeView
                    self.controller.storage.set_pending_seed(
                        Seed(mnemonic=seed_mnemonic, wordlist_language_code=self.wordlist_language_code)
                    )
                    if self.settings.get_value(SettingsConstants.SETTING__PASSPHRASE) == SettingsConstants.OPTION__REQUIRED:
                        from seedsigner.views.seed_views import SeedAddPassphraseView
                        return Destination(SeedAddPassphraseView)
                    else:
                        return Destination(SeedFinalizeView)
            
            elif self.decoder.is_settings:
                from seedsigner.views.settings_views import SettingsIngestSettingsQRView
                data = self.decoder.get_settings_data()
                return Destination(SettingsIngestSettingsQRView, view_args=dict(data=data))

            elif self.decoder.is_cardano_account_request:
                from seedsigner.views.seed_views import CardanoExportSelectSeedView
                try:
                    self.controller.cardano_account_request = self.decoder.get_cardano_account_request()
                except Exception as e:
                    logger.info(repr(e), exc_info=True)
                    return Destination(ErrorView, view_args=dict(
                        title="Error",
                        status_headline=_("Invalid Request"),
                        text=_("Could not read the account key request.") + "\n" + _error_detail(e),
                        button_text="Back",
                        next_destination=Destination(BackStackView, skip_current_view=True),
                    ))
                return Destination(CardanoExportSelectSeedView, skip_current_view=True)

            elif self.decoder.is_cardano_tx_sign_request:
                from seedsigner.views.seed_views import CardanoTxSelectSeedView
                try:
                    self.controller.cardano_tx_sign_request = self.decoder.get_cardano_tx_sign_request()
                except Exception as e:
                    logger.info(repr(e), exc_info=True)
                    return Destination(ErrorView, view_args=dict(
                        title="Error",
                        status_headline=_("Invalid Request"),
                        text=_("Could not read the transaction sign request.") + "\n" + _error_detail(e),
                        button_text="Back",
                        next_destination=Destination(BackStackView, skip_current_view=True),
                    ))
                return Destination(CardanoTxSelectSeedView, skip_current_view=True)

            elif self.decoder.is_cardano_cip8_sign_request:
                from seedsigner.views.seed_views import CardanoMsgSelectSeedView
                try:
                    self.controller.cardano_cip8_sign_request = self.decoder.get_cardano_cip8_sign_request()
                except Exception as e:
                    logger.info(repr(e), exc_info=True)
                    return Destination(ErrorView, view_args=dict(
                        title="Error",
                        status_headline=_("Invalid Request"),
                        text=_("Could not read the message sign request.") + "\n" + _error_detail(e),
                        button_text="Back",
                        next_destination=Destination(BackStackView, skip_current_view=True),
                    ))
                return Destination(CardanoMsgSelectSeedView, skip_current_view=True)

            else:
                return Destination(NotYetImplementedView)

        elif self.decoder.is_invalid:
            # For now, don't even try to re-do the attempted operation, just reset and
            # start everything over.
            self.controller.resume_main_flow = None
            return Destination(ScanInvalidQRTypeView)

        return Destination(MainMenuView)



class ScanSeedQRView(ScanView):
    instructions_text = _mft("Scan SeedQR")
    invalid_qr_type_message = _mft("Expected a SeedQR")

    @property
    def is_valid_qr_type(self):
        return self.decoder.is_seed



class ScanInvalidQRTypeView(View):
    def run(self):
        from seedsigner.gui.screens import WarningScreen

        # TODO: This screen says "Error" but is intentionally using the WarningScreen in
        # order to avoid the perception that something is broken on our end. This should
        # either change to use the red ErrorScreen or the "Error" title should be
        # changed to something softer.
        self.run_screen(
            WarningScreen,
            title=_("Error"),
            status_headline=_("Unknown QR Type"),
            text=_("QRCode is invalid or is a data format not yet supported."),
            button_data=[ButtonOption("Back to Main Menu")],
        )

        return Destination(MainMenuView, clear_history=True)

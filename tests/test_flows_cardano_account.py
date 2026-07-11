"""
Flow tests for the scan-initiated Cardano account export.

Drives MainMenu -> Scan (inject a cardano-account-req) -> seed selection ->
consent / multi-account gate -> animated QR display.
"""

from base import BaseTest, FlowTest, FlowStep

from seedsigner.models.settings import Settings, SettingsConstants
from seedsigner.models.seed import Seed
from seedsigner.views.view import MainMenuView
from seedsigner.views import seed_views, scan_views


ABANDON_MNEMONIC = (
    "abandon abandon abandon abandon abandon abandon abandon abandon "
    "abandon abandon abandon about"
).split()


def inject_account_request(account_indices):
    def _inject(view: scan_views.ScanView):
        from seedsigner.helpers.ur2.ur_encoder import UREncoder
        from seedsigner.helpers.ur2.ur import UR
        from seedsigner.models.cardano_account import CardanoAccountRequest
        from seedsigner.models.decode_qr import DecodeQRStatus

        request = CardanoAccountRequest(request_id="t", account_indices=account_indices)
        encoder = UREncoder(ur=UR("cardano-account-req", bytearray(request.to_cbor())), max_fragment_len=200)
        status = None
        while status != DecodeQRStatus.COMPLETE:
            status = view.decoder.add_data(encoder.next_part().upper())
    return _inject


class TestCardanoAccountExportFlows(FlowTest):

    def _load_seed(self):
        self.controller.storage.set_pending_seed(Seed(mnemonic=ABANDON_MNEMONIC))
        self.controller.storage.finalize_pending_seed()

    def test_export_single_account_scan_flow(self):
        Settings.get_instance().set_value(SettingsConstants.SETTING__PRIVACY_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self._load_seed()

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_account_request([0])),
            FlowStep(seed_views.CardanoExportSelectSeedView, is_redirect=True),
            FlowStep(seed_views.CardanoExportAccountKeyConsentView, is_redirect=True),
            FlowStep(seed_views.CardanoExportAccountKeyDetailsView, screen_return_value=0),
            FlowStep(seed_views.CardanoExportAccountKeyQRView),
        ])

    def test_export_multi_account_when_enabled(self):
        Settings.get_instance().set_value(SettingsConstants.SETTING__MULTI_ACCOUNTS, SettingsConstants.OPTION__ENABLED)
        Settings.get_instance().set_value(SettingsConstants.SETTING__PRIVACY_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self._load_seed()

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_account_request([0, 1])),
            FlowStep(seed_views.CardanoExportSelectSeedView, is_redirect=True),
            FlowStep(seed_views.CardanoExportAccountKeyConsentView, is_redirect=True),
            FlowStep(seed_views.CardanoExportAccountKeyDetailsView, screen_return_value=0),
            FlowStep(seed_views.CardanoExportAccountKeyDetailsView, screen_return_value=0),
            FlowStep(seed_views.CardanoExportAccountKeyQRView),
        ])

    def test_export_multi_account_gate_when_disabled(self):
        Settings.get_instance().set_value(SettingsConstants.SETTING__MULTI_ACCOUNTS, SettingsConstants.OPTION__DISABLED)
        self._load_seed()

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SCAN),
            FlowStep(scan_views.ScanView, before_run=inject_account_request([0, 1])),
            FlowStep(seed_views.CardanoExportSelectSeedView, is_redirect=True),
            FlowStep(seed_views.CardanoExportAccountKeyConsentView, screen_return_value=0),
            FlowStep(MainMenuView),
        ])

    def test_export_xpub_menu_flow(self):
        Settings.get_instance().set_value(SettingsConstants.SETTING__PRIVACY_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self._load_seed()

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_ACCOUNT_KEY),
                FlowStep(seed_views.CardanoExportAccountKeyView, is_redirect=True),
                FlowStep(seed_views.CardanoExportAccountKeySelectView, screen_return_value=0),
                FlowStep(seed_views.CardanoExportAccountKeyDetailsView, screen_return_value=0),
                FlowStep(seed_views.CardanoExportAccountKeyQRView),
            ],
        )

    def test_export_xpub_menu_flow_nondefault_account(self):
        Settings.get_instance().set_value(SettingsConstants.SETTING__PRIVACY_WARNINGS, SettingsConstants.OPTION__DISABLED)
        self._load_seed()

        self.run_sequence(
            initial_destination_view_args=dict(seed_num=0),
            sequence=[
                FlowStep(seed_views.SeedOptionsView, button_data_selection=seed_views.SeedOptionsView.EXPORT_ACCOUNT_KEY),
                FlowStep(seed_views.CardanoExportAccountKeyView, is_redirect=True),
                FlowStep(seed_views.CardanoExportAccountKeySelectView, screen_return_value=3),
                FlowStep(seed_views.CardanoExportAccountKeyDetailsView, screen_return_value=0),
                FlowStep(seed_views.CardanoExportAccountKeyQRView),
            ],
        )

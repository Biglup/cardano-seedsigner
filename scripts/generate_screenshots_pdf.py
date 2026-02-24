#!/usr/bin/env python3
"""Generate a PDF catalog of SeedSigner screenshots."""

import os
from fpdf import FPDF

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "seedsigner-screenshots", "en")
OUTPUT_PDF = os.path.join(os.path.dirname(__file__), "..", "seedsigner-screenshots", "SeedSigner_Screenshots.pdf")

# Section definitions: (directory_name, section_title, {filename: friendly_name})
SECTIONS = [
    ("main_menu_views", "Main Menu", {
        "OpeningSplashView": "Opening Splash Screen",
        "MainMenuView": "Main Menu",
        "PowerOptionsView": "Power Options",
        "PowerOffView": "Power Off Confirmation",
        "RestartView": "Restart Confirmation",
        "RemoveMicroSDWarningView": "Remove MicroSD Warning",
        "MainMenuView_DefaultToast": "Toast: Default",
        "MainMenuView_InfoToast": "Toast: Info",
        "MainMenuView_SuccessToast": "Toast: Success",
        "MainMenuView_WarningToast": "Toast: Warning",
        "MainMenuView_DireWarningToast": "Toast: Dire Warning",
        "MainMenuView_ErrorToast": "Toast: Error",
        "MainMenuView_SDCardStateChangeToast_inserted": "Toast: SD Card Inserted",
        "MainMenuView_SDCardStateChangeToast_removed": "Toast: SD Card Removed",
        "MainMenuView_RemoveSDCardToast": "Toast: Remove SD Card",
    }),
    ("seed_views", "Seed Management", {
        "SeedsMenuView": "Seeds Menu",
        "LoadSeedView": "Load Seed",
        "SeedMnemonicEntryView": "Mnemonic Word Entry",
        "SeedMnemonicInvalidView": "Invalid Mnemonic Warning",
        "SeedFinalizeView": "Finalize Seed",
        "SeedOptionsView": "Seed Options Menu",
        "SeedBackupView": "Seed Backup Options",
        "SeedWordsView": "Seed Words (Page 1)",
        "SeedWordsView_2": "Seed Words (Page 2)",
        "SeedWordsWarningView": "Seed Words Warning",
        "SeedWordsBackupTestPromptView": "Backup Verification Prompt",
        "SeedWordsBackupTestView": "Backup Verification Quiz",
        "SeedWordsBackupTestMistakeView": "Backup Verification Mistake",
        "SeedWordsBackupTestSuccessView": "Backup Verification Success",
        "SeedAddPassphraseView_lowercase": "Passphrase Entry (Lowercase)",
        "SeedAddPassphraseView_uppercase": "Passphrase Entry (Uppercase)",
        "SeedAddPassphraseView_digits": "Passphrase Entry (Digits)",
        "SeedAddPassphraseView_symbols_1": "Passphrase Entry (Symbols 1)",
        "SeedAddPassphraseView_symbols_2": "Passphrase Entry (Symbols 2)",
        "SeedAddPassphraseExitDialogView": "Passphrase Exit Dialog",
        "SeedReviewPassphraseView": "Review Passphrase",
        "SeedDiscardView": "Discard Seed Confirmation",
        "SeedExportXpubSigTypeView": "Export Xpub: Signature Type",
        "SeedExportXpubScriptTypeView": "Export Xpub: Script Type",
        "SeedExportXpubCustomDerivationView": "Export Xpub: Custom Derivation",
        "SeedExportXpubWarningView": "Export Xpub: Warning",
        "SeedExportXpubDetailsView": "Export Xpub: Details",
        "SeedExportXpubQR_ScreenBrightnessView": "Export Xpub: QR Brightness",
        "SeedTranscribeSeedQRFormatView": "SeedQR: Format Selection",
        "SeedTranscribeSeedQRWarningView": "SeedQR: Transcription Warning",
        "SeedTranscribeSeedQRWholeQRView_12_Standard": "SeedQR: 12-Word Standard",
        "SeedTranscribeSeedQRWholeQRView_12_Compact": "SeedQR: 12-Word Compact",
        "SeedTranscribeSeedQRWholeQRView_24_Standard": "SeedQR: 24-Word Standard",
        "SeedTranscribeSeedQRWholeQRView_24_Compact": "SeedQR: 24-Word Compact",
        "SeedTranscribeSeedQRZoomedInView_12_Compact": "SeedQR: Zoomed In (12-Word Compact)",
        "SeedTranscribeSeedQRZoomedInView_12_Standard": "SeedQR: Zoomed In (12-Word Standard)",
        "SeedTranscribeSeedQRConfirmQRPromptView": "SeedQR: Confirm QR Prompt",
        "SeedTranscribeSeedQRConfirmSuccessView": "SeedQR: Confirm Success",
        "SeedTranscribeSeedQRConfirmWrongSeedView": "SeedQR: Wrong Seed Warning",
        "SeedTranscribeSeedQRConfirmInvalidQRView": "SeedQR: Invalid QR Warning",
        "AddressVerificationSigTypeView": "Address Verification: Sig Type",
        "SeedSelectSeedView_address_verification": "Select Seed for Address Verification",
        "SeedAddressVerificationView": "Address Verification",
        "SeedAddressVerificationSuccessView": "Address Verification Success",
        "SeedSelectSeedView_sign_message": "Select Seed for Message Signing",
        "SeedSignMessageConfirmAddressView": "Message Signing: Confirm Address",
        "SeedSignMessageConfirmMessageView": "Message Signing: Confirm Message",
        "SeedBIP85SelectNumWordsView": "BIP-85: Select Word Count",
        "SeedBIP85SelectChildIndexView": "BIP-85: Select Child Index",
        "SeedBIP85InvalidChildIndexView": "BIP-85: Invalid Child Index",
    }),
    ("cardano_tx_views", "Cardano Transaction Review", {
        "CardanoTxOverviewView": "Transaction Overview",
        "SeqReview_output_first": "Output (ADA Only)",
        "SeqReview_output_with_tokens": "Output (With Tokens)",
        "SeqReview_fee": "Fee",
        "SeqReview_validity_start": "Validity Start",
        "SeqReview_ttl": "Time To Live (TTL)",
        "SeqReview_certificate": "Certificate",
        "SeqReview_withdrawal": "Withdrawal",
        "SeqReview_aux_data_hash": "Auxiliary Data Hash",
        "SeqReview_mint": "Mint / Burn",
        "SeqReview_script_data_hash": "Script Data Hash",
        "SeqReview_required_signer": "Required Signer",
        "SeqReview_collateral_return": "Collateral Return",
        "SeqReview_total_collateral": "Total Collateral",
        "SeqReview_ref_input": "Reference Input",
        "SeqReview_voting": "Governance Vote",
        "SeqReview_proposal": "Governance Proposal",
        "SeqReview_treasury": "Treasury",
        "SeqReview_donation": "Donation",
        "CardanoTxSignView": "Sign Transaction",
        "CardanoMsgOverviewView": "Message Signing Overview",
        "CardanoMsgAddressView": "Message Signing Address",
        "CardanoMsgPayloadView": "Message Signing Payload",
        "CardanoMsgSignView": "Sign Message",
    }),
    ("tools_views", "Tools", {
        "ToolsMenuView": "Tools Menu",
        "ToolsImageEntropyMnemonicLengthView": "Image Entropy: Word Count",
        "ToolsDiceEntropyMnemonicLengthView": "Dice Entropy: Word Count",
        "ToolsDiceEntropyEntryView": "Dice Entropy: Entry",
        "ToolsCalcFinalWordNumWordsView": "Calculate Final Word: Word Count",
        "ToolsCalcFinalWordFinalizePromptView": "Calculate Final Word: Finalize",
        "ToolsCalcFinalWordCoinFlipsView": "Calculate Final Word: Coin Flips",
        "ToolsCalcFinalWordShowFinalWordView_pick_word": "Calculate Final Word: Result (Pick Word)",
        "ToolsCalcFinalWordShowFinalWordView_coin_flips": "Calculate Final Word: Result (Coin Flips)",
        "ToolsCalcFinalWordDoneView": "Calculate Final Word: Done",
        "ToolsAddressExplorerSelectSourceView": "Address Explorer: Select Source",
        "ToolsAddressExplorerAddressTypeView": "Address Explorer: Address Type",
        "ToolsAddressExplorerAddressListView": "Address Explorer: Address List",
    }),
    ("settings_views", "Settings", {
        "SettingsMenuView": "Settings Menu",
        "SettingsEntryUpdateSelectionView_persistent_settings": "Persistent Settings",
        "SettingsEntryUpdateSelectionView_qr_density": "QR Code Density",
        "SettingsEntryUpdateSelectionView_xpub_export": "Xpub Export",
        "SettingsEntryUpdateSelectionView_xpub_details": "Xpub Details",
        "SettingsEntryUpdateSelectionView_passphrase": "Passphrase",
        "SettingsEntryUpdateSelectionView_camera_rotation": "Camera Rotation",
        "SettingsEntryUpdateSelectionView_compact_seedqr": "Compact SeedQR",
        "SettingsEntryUpdateSelectionView_bip85_child_seeds": "BIP-85 Child Seeds",
        "SettingsEntryUpdateSelectionView_microsd_toast_timer": "MicroSD Toast Timer",
        "SettingsEntryUpdateSelectionView_privacy_warnings": "Privacy Warnings",
        "SettingsEntryUpdateSelectionView_dire_warnings": "Dire Warnings",
        "SettingsEntryUpdateSelectionView_qr_brightness_tips": "QR Brightness Tips",
        "SettingsMenuView__Hardware": "Hardware Settings",
        "SettingsEntryUpdateSelectionView_display_config": "Display Configuration",
        "SettingsEntryUpdateSelectionView_color_inverted": "Color Inverted",
        "IOTestView": "I/O Test",
        "SettingsIngestSettingsQRView_persistent": "Ingest Settings QR (Persistent)",
        "SettingsIngestSettingsQRView_not_persistent": "Ingest Settings QR (Not Persistent)",
    }),
    ("misc_error_views", "Error Screens", {
        "NotYetImplementedView": "Not Yet Implemented",
        "UnhandledExceptionView": "Unhandled Exception",
        "CameraConnectionErrorView": "Camera Connection Error",
        "NetworkMismatchErrorView": "Network Mismatch Error",
        "OptionDisabledView": "Option Disabled",
        "ScanInvalidQRTypeView": "Invalid QR Type",
    }),
]


class ScreenshotPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "Cardano SeedSigner - UI Screenshots", align="C")
            self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(160, 160, 160)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def build_pdf():
    pdf = ScreenshotPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_top_margin(18)  # Leave room for the page header

    # ── Cover page ──
    pdf.add_page()
    pdf.ln(60)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(63, 81, 181)  # Cardano Indigo Blue
    pdf.cell(0, 14, "Cardano SeedSigner", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 10, "User Interface Screenshots", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Screenshot sections ──
    COLS = 3
    IMG_W = 48       # mm per image
    IMG_H = 48       # mm height for the image (square 240x240)
    LBL_GAP = 1      # mm gap between image and label
    LBL_H = 6        # mm height for the label
    CELL_H = IMG_H + LBL_GAP + LBL_H  # total cell height
    ROW_GAP = 4      # mm gap between rows
    PAGE_W = 210
    MARGIN = 15
    TABLE_W = PAGE_W - 2 * MARGIN
    COL_W = TABLE_W / COLS
    IMG_X_OFFSET = (COL_W - IMG_W) / 2  # center image in cell

    for dir_name, section_title, name_map in SECTIONS:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(63, 81, 181)
        pdf.cell(0, 12, section_title, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        items = list(name_map.items())
        for i, (filename, friendly_name) in enumerate(items):
            col = i % COLS
            if col == 0:
                # Check if we need a new page
                if pdf.get_y() + CELL_H > pdf.h - 20:
                    pdf.add_page()
                row_y = pdf.get_y()

            img_path = os.path.join(SCREENSHOTS_DIR, dir_name, f"{filename}.png")
            if not os.path.exists(img_path):
                print(f"  WARNING: missing {img_path}")
                continue

            cell_x = MARGIN + col * COL_W
            # Place image centered in cell
            pdf.image(img_path, x=cell_x + IMG_X_OFFSET, y=row_y, w=IMG_W)
            # Place label tight below image
            pdf.set_xy(cell_x, row_y + IMG_H + LBL_GAP)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(COL_W, LBL_H, friendly_name, align="C")

            if col == COLS - 1 or i == len(items) - 1:
                pdf.set_y(row_y + CELL_H + ROW_GAP)

    pdf.output(OUTPUT_PDF)
    print(f"PDF saved to: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()

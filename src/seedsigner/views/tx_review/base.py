"""
Base class for sequential section review views.

Provides shared navigation logic so each section view only needs
to implement its own render() method.
"""

from gettext import gettext as _

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoParsedTx
from seedsigner.views.view import View, Destination, BackStackView, MainMenuView


class BaseSequentialSectionView(View):
    """Base for all section-specific sequential review views.

    Subclasses set `section_title` and implement `render()`.
    Navigation (left/right/back/sign) is handled here.
    """

    section_title: str = ""

    def __init__(self, parsed_tx: CardanoParsedTx, global_index: int = 0):
        super().__init__()
        self.parsed_tx = parsed_tx
        self.global_index = global_index
        self.pages = parsed_tx.build_review_pages()

    def run(self):
        """Render the current page and route the result.

        Both chevrons are always shown: on the first page the left chevron
        goes back to the overview.
        """
        page = self.pages[self.global_index]
        total_pages = len(self.pages)

        if page.total_in_section > 1:
            title = f"{self.section_title} {page.item_index + 1}/{page.total_in_section}"
        else:
            title = self.section_title

        result = self.render(page, title, True, True, total_pages)
        return self._handle_navigation(result, total_pages)

    def render(self, page, title, has_left, has_right, total_pages):
        """Override in subclasses to render the section-specific screen."""
        raise NotImplementedError

    def render_generic(self, content_lines, title, has_left, has_right, total_pages):
        """Helper for sections using the generic CardanoTxSequentialScreen."""
        from seedsigner.gui.screens.tx_review import CardanoTxSequentialScreen

        return self.run_screen(
            CardanoTxSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content_lines=content_lines,
        )

    def reject_undisplayable(self, element_name):
        """Refuse to sign a transaction containing an element the device
        cannot decode for display.

        The user must be able to review everything they sign, so show a dire
        warning, clear the pending sign request and exit to the main menu so
        the sign confirmation can never be reached.
        """
        from seedsigner.gui.screens.screen import ButtonOption, DireWarningScreen

        self.run_screen(
            DireWarningScreen,
            title=_("Cannot Display"),
            status_headline=_("TX Rejected"),
            text=_("This transaction contains a {} this device cannot display. It will not be signed.").format(element_name),
            show_back_button=False,
            button_data=[ButtonOption("OK")],
        )
        self.controller.cardano_tx_sign_request = None
        self.controller.cardano_seed = None
        self.controller.resume_main_flow = None
        return Destination(MainMenuView, clear_history=True)

    def _handle_navigation(self, result, total_pages):
        """Route the screen result to the previous/next page, to the signing-keys
        step once past the last page, or back."""
        from .signing_keys_view import CardanoTxSigningKeysView
        from .sequential_review_view import CardanoTxSequentialReviewView

        if isinstance(result, Destination):
            return result

        is_last_page = self.global_index >= total_pages - 1

        if result == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if result == RET_CODE__LEFT_BUTTON:
            if self.global_index > 0:
                return Destination(
                    CardanoTxSequentialReviewView,
                    view_args=dict(parsed_tx=self.parsed_tx, global_index=self.global_index - 1),
                    skip_current_view=True,
                )
            return Destination(BackStackView)

        if result == RET_CODE__RIGHT_BUTTON:
            if is_last_page:
                return Destination(CardanoTxSigningKeysView, view_args=dict(parsed_tx=self.parsed_tx))
            return Destination(
                CardanoTxSequentialReviewView,
                view_args=dict(parsed_tx=self.parsed_tx, global_index=self.global_index + 1),
                skip_current_view=True,
            )

        return Destination(BackStackView)

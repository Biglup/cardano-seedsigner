"""
Unified sequential review dispatcher.

Routes each review page to its section-specific view class.
"""

from seedsigner.models.cardano_tx import CardanoParsedTx

from seedsigner.views.view import View, Destination, BackStackView

from .output_view import OutputReviewView
from .fee_view import FeeReviewView
from .ttl_view import TtlReviewView
from .certificate_view import CertificateReviewView
from .withdrawal_view import WithdrawalReviewView
from .aux_data_hash_view import AuxDataHashReviewView
from .validity_start_view import ValidityStartReviewView
from .mint_view import MintReviewView
from .script_data_hash_view import ScriptDataHashReviewView
from .collateral_view import CollateralReviewView
from .required_signer_view import RequiredSignerReviewView
from .network_id_view import NetworkIdReviewView
from .collateral_return_view import CollateralReturnReviewView
from .total_collateral_view import TotalCollateralReviewView
from .reference_input_view import ReferenceInputReviewView
from .voting_view import VotingReviewView
from .proposal_view import ProposalReviewView
from .treasury_view import TreasuryReviewView
from .donation_view import DonationReviewView


# Section name -> view class
_SECTION_VIEW_MAP = {
    "output": OutputReviewView,
    "fee": FeeReviewView,
    "ttl": TtlReviewView,
    "certificate": CertificateReviewView,
    "withdrawal": WithdrawalReviewView,
    "aux_data_hash": AuxDataHashReviewView,
    "validity_start": ValidityStartReviewView,
    "mint": MintReviewView,
    "script_data_hash": ScriptDataHashReviewView,
    "collateral": CollateralReviewView,
    "required_signer": RequiredSignerReviewView,
    "network_id": NetworkIdReviewView,
    "collateral_return": CollateralReturnReviewView,
    "total_collateral": TotalCollateralReviewView,
    "reference_input": ReferenceInputReviewView,
    "voting": VotingReviewView,
    "proposal": ProposalReviewView,
    "treasury": TreasuryReviewView,
    "donation": DonationReviewView,
}


class CardanoTxSequentialReviewView(View):
    """
    Dispatcher that routes to the correct section view based on the
    current page's section name.
    """

    def __init__(self, parsed_tx: CardanoParsedTx, global_index: int = 0):
        super().__init__()
        self.parsed_tx = parsed_tx
        self.global_index = global_index

    def run(self):
        pages = self.parsed_tx.build_review_pages()
        page = pages[self.global_index]

        view_cls = _SECTION_VIEW_MAP.get(page.section)
        if view_cls is None:
            return Destination(BackStackView)

        view = view_cls(parsed_tx=self.parsed_tx, global_index=self.global_index)
        return view.run()

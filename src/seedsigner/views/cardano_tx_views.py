"""
Cardano Transaction Review Views

Views for reviewing and signing Cardano transactions.
Sequential navigation: Overview → left/right through ALL fields in CBOR key order → Sign
"""

from gettext import gettext as _

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON
from seedsigner.gui.screens.tx_review import (
    format_ada,
    RET_CODE__LEFT_BUTTON,
    RET_CODE__RIGHT_BUTTON,
)
from seedsigner.models.cardano_tx import CardanoParsedTx

from .view import View, Destination, BackStackView, MainMenuView


# =============================================================================
# Content line builders for sequential screens
# =============================================================================

def _cert_content_lines(cert) -> list[str]:
    """Build display lines for a certificate."""
    ct = cert.cert_type
    lines = [f"### {ct.name}"]

    try:
        if ct.name == "STAKE_REGISTRATION":
            lines.append(f"Credential: {cert.to_stake_registration().credential.hash_hex[:16]}...")
        elif ct.name == "STAKE_DEREGISTRATION":
            lines.append(f"Credential: {cert.to_stake_deregistration().credential.hash_hex[:16]}...")
        elif ct.name == "STAKE_DELEGATION":
            sd = cert.to_stake_delegation()
            lines.append(f"Pool: {sd.pool_key_hash}")
            lines.append(f"Credential: {sd.credential.hash_hex[:16]}...")
        elif ct.name == "POOL_REGISTRATION":
            pr = cert.to_pool_registration()
            p = pr.params
            lines.append(f"Operator: {p.operator_key_hash}")
            lines.append(f"**Pledge: {format_ada(p.pledge)}")
            lines.append(f"**Cost: {format_ada(p.cost)}")
            lines.append(f"Margin: {p.margin}")
            lines.append(f"VRF: {p.vrf_vk_hash}")
            lines.append(f"Reward: {p.reward_account}")
            owners = p.owners
            lines.append(f"Owners: {len(owners)}")
            relays = p.relays
            lines.append(f"Relays: {len(relays)}")
            if p.metadata:
                lines.append(f"Metadata URL:")
                lines.append(f"  {p.metadata.url}")
        elif ct.name == "POOL_RETIREMENT":
            pr = cert.to_pool_retirement()
            lines.append(f"Pool: {pr.pool_key_hash}")
            lines.append(f"Epoch: {pr.epoch}")
        elif ct.name == "REGISTRATION":
            r = cert.to_registration()
            lines.append(f"Credential: {r.credential.hash_hex[:16]}...")
            lines.append(f"**Deposit: {format_ada(r.deposit)}")
        elif ct.name == "UNREGISTRATION":
            u = cert.to_unregistration()
            lines.append(f"Credential: {u.credential.hash_hex[:16]}...")
            lines.append(f"**Deposit: {format_ada(u.deposit)}")
        elif ct.name == "VOTE_DELEGATION":
            vd = cert.to_vote_delegation()
            lines.append(f"Credential: {vd.credential.hash_hex[:16]}...")
            lines.append(f"DRep: {vd.drep}")
        elif ct.name == "STAKE_VOTE_DELEGATION":
            svd = cert.to_stake_vote_delegation()
            lines.append(f"Credential: {svd.credential.hash_hex[:16]}...")
            lines.append(f"Pool: {svd.pool_key_hash}")
            lines.append(f"DRep: {svd.drep}")
        elif ct.name == "STAKE_REGISTRATION_DELEGATION":
            srd = cert.to_stake_registration_delegation()
            lines.append(f"Credential: {srd.credential.hash_hex[:16]}...")
            lines.append(f"Pool: {srd.pool_key_hash}")
            lines.append(f"**Deposit: {format_ada(srd.deposit)}")
        elif ct.name == "VOTE_REGISTRATION_DELEGATION":
            vrd = cert.to_vote_registration_delegation()
            lines.append(f"Credential: {vrd.credential.hash_hex[:16]}...")
            lines.append(f"DRep: {vrd.drep}")
            lines.append(f"**Deposit: {format_ada(vrd.deposit)}")
        elif ct.name == "STAKE_VOTE_REGISTRATION_DELEGATION":
            svrd = cert.to_stake_vote_registration_delegation()
            lines.append(f"Credential: {svrd.credential.hash_hex[:16]}...")
            lines.append(f"Pool: {svrd.pool_key_hash}")
            lines.append(f"DRep: {svrd.drep}")
            lines.append(f"**Deposit: {format_ada(svrd.deposit)}")
        elif ct.name == "AUTH_COMMITTEE_HOT":
            ach = cert.to_authorize_committee_hot()
            lines.append(f"Cold: {ach.committee_cold_credential.hash_hex[:16]}...")
            lines.append(f"Hot: {ach.committee_hot_credential.hash_hex[:16]}...")
        elif ct.name == "RESIGN_COMMITTEE_COLD":
            rcc = cert.to_resign_committee_cold()
            lines.append(f"Cold: {rcc.committee_cold_credential.hash_hex[:16]}...")
            if rcc.anchor:
                lines.append(f"Anchor: {rcc.anchor.url}")
        elif ct.name == "DREP_REGISTRATION":
            rd = cert.to_register_drep()
            lines.append(f"Credential: {rd.credential.hash_hex[:16]}...")
            lines.append(f"**Deposit: {format_ada(rd.deposit)}")
            if rd.anchor:
                lines.append(f"Anchor: {rd.anchor.url}")
        elif ct.name == "DREP_UNREGISTRATION":
            ud = cert.to_unregister_drep()
            lines.append(f"Credential: {ud.credential.hash_hex[:16]}...")
            lines.append(f"**Deposit: {format_ada(ud.deposit)}")
        elif ct.name == "UPDATE_DREP":
            ud = cert.to_update_drep()
            lines.append(f"Credential: {ud.credential.hash_hex[:16]}...")
            if ud.anchor:
                lines.append(f"Anchor: {ud.anchor.url}")
        else:
            lines.append(f"Type value: {ct.value}")
    except Exception:
        lines.append("(parse error)")

    return lines


def _withdrawal_content_lines(reward_addr, amount) -> list[str]:
    """Build display lines for a withdrawal."""
    addr_str = str(reward_addr)
    lines = [
        "### Withdrawal",
        f"**{format_ada(amount)}",
        f"Address:",
        f"  {addr_str[:24]}...",
        f"  ...{addr_str[-16:]}",
    ]
    return lines


def _mint_content_lines(policy_id, asset_map) -> list[str]:
    """Build display lines for a minting policy."""
    pid_str = str(policy_id)
    lines = [
        "### Mint/Burn",
        f"Policy:",
        f"  {pid_str[:24]}...",
    ]
    for asset_name, qty in asset_map.items():
        name_str = str(asset_name) if str(asset_name) else "(empty)"
        sign = "+" if qty > 0 else ""
        lines.append(f"**{name_str}: {sign}{qty:,}")
    return lines


def _voting_content_lines(voter, action_id, proc) -> list[str]:
    """Build display lines for a voting procedure."""
    lines = [
        f"### {voter.voter_type.name}",
        f"Action:",
        f"  {action_id.hash_hex[:20]}...",
        f"  Index: {action_id.index}",
        f"**Vote: {proc.vote.name}",
    ]
    if proc.anchor:
        lines.append(f"Anchor: {proc.anchor.url}")
    return lines


def _proposal_content_lines(proposal) -> list[str]:
    """Build display lines for a governance proposal."""
    lines = [
        f"### {proposal.action_type.name}",
        f"**Deposit: {format_ada(proposal.deposit)}",
    ]
    if proposal.anchor:
        lines.append(f"Anchor:")
        lines.append(f"  {proposal.anchor.url}")
    return lines


def _input_content_lines(inp) -> list[str]:
    """Build display lines for a transaction input."""
    tx_id = str(inp.transaction_id)
    lines = [
        "### Input",
        f"TX Hash:",
        f"  {tx_id[:24]}...",
        f"  ...{tx_id[-16:]}",
        f"Index: {inp.index}",
    ]
    return lines


def _fee_content_lines(fee) -> list[str]:
    """Build display lines for the fee."""
    return [
        "### Fee",
        f"**{format_ada(fee)}",
    ]


def _ttl_content_lines(ttl) -> list[str]:
    """Build display lines for TTL (invalid after)."""
    return [
        "### TTL (Invalid After)",
        f"Slot: {ttl:,}",
    ]


def _validity_start_content_lines(slot) -> list[str]:
    """Build display lines for validity interval start."""
    return [
        "### Valid From",
        f"Slot: {slot:,}",
    ]


def _aux_data_hash_content_lines(hash_val) -> list[str]:
    """Build display lines for auxiliary data hash."""
    h = str(hash_val)
    return [
        "### Auxiliary Data Hash",
        f"  {h[:32]}",
        f"  {h[32:]}",
    ]


def _script_data_hash_content_lines(hash_val) -> list[str]:
    """Build display lines for script data hash."""
    h = str(hash_val)
    return [
        "### Script Data Hash",
        f"  {h[:32]}",
        f"  {h[32:]}",
    ]


def _required_signer_content_lines(signer) -> list[str]:
    """Build display lines for a required signer."""
    s = str(signer)
    return [
        "### Required Signer",
        f"  {s[:32]}",
        f"  {s[32:]}",
    ]


def _network_id_content_lines(network_id) -> list[str]:
    """Build display lines for network ID."""
    name = "Mainnet" if network_id == 1 else "Testnet"
    return [
        "### Network ID",
        f"**{name} ({network_id})",
    ]


def _collateral_return_content_lines(output) -> list[str]:
    """Build display lines for collateral return output."""
    addr_str = str(output.address)
    lines = [
        "### Collateral Return",
        f"**{format_ada(output.value.coin)}",
        f"Address:",
        f"  {addr_str[:24]}...",
        f"  ...{addr_str[-16:]}",
    ]
    return lines


def _total_collateral_content_lines(amount) -> list[str]:
    """Build display lines for total collateral."""
    return [
        "### Total Collateral",
        f"**{format_ada(amount)}",
    ]


def _treasury_content_lines(amount) -> list[str]:
    """Build display lines for treasury."""
    return [
        "### Treasury",
        f"**{format_ada(amount)}",
    ]


def _donation_content_lines(amount) -> list[str]:
    """Build display lines for donation."""
    return [
        "### Donation",
        f"**{format_ada(amount)}",
    ]


# Section name -> content_lines builder
_SECTION_CONTENT_BUILDERS = {
    "fee": lambda data: _fee_content_lines(data),
    "ttl": lambda data: _ttl_content_lines(data),
    "certificate": lambda data: _cert_content_lines(data),
    "withdrawal": lambda data: _withdrawal_content_lines(*data),
    "aux_data_hash": lambda data: _aux_data_hash_content_lines(data),
    "validity_start": lambda data: _validity_start_content_lines(data),
    "mint": lambda data: _mint_content_lines(*data),
    "script_data_hash": lambda data: _script_data_hash_content_lines(data),
    "collateral": lambda data: _input_content_lines(data),
    "required_signer": lambda data: _required_signer_content_lines(data),
    "network_id": lambda data: _network_id_content_lines(data),
    "collateral_return": lambda data: _collateral_return_content_lines(data),
    "total_collateral": lambda data: _total_collateral_content_lines(data),
    "reference_input": lambda data: _input_content_lines(data),
    "voting": lambda data: _voting_content_lines(*data),
    "proposal": lambda data: _proposal_content_lines(data),
    "treasury": lambda data: _treasury_content_lines(data),
    "donation": lambda data: _donation_content_lines(data),
}

# Section name -> display title
_SECTION_TITLES = {
    "output": "Output",
    "fee": "Fee",
    "ttl": "TTL",
    "certificate": "Certificate",
    "withdrawal": "Withdrawal",
    "aux_data_hash": "Aux Data Hash",
    "validity_start": "Valid From",
    "mint": "Mint/Burn",
    "script_data_hash": "Script Data Hash",
    "collateral": "Collateral",
    "required_signer": "Required Signer",
    "network_id": "Network ID",
    "collateral_return": "Collateral Return",
    "total_collateral": "Total Collateral",
    "reference_input": "Ref Input",
    "voting": "Vote",
    "proposal": "Proposal",
    "treasury": "Treasury",
    "donation": "Donation",
}


# =============================================================================
# Cardano Transaction Views
# =============================================================================

class CardanoTxOverviewView(View):
    """
    TX Overview - First screen showing animated flow diagram.
    Shows: inputs -> recipients + fee + change with animated lines.
    Button: "Review details" -> enters sequential review
    """

    def __init__(self, parsed_tx: CardanoParsedTx = None):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoTxOverviewScreen

        num_change = len(self.parsed_tx.verified_change_indices)

        selected_menu_num = self.run_screen(
            CardanoTxOverviewScreen,
            spend_amount=self.parsed_tx.sending_amount,
            num_inputs=len(self.parsed_tx.inputs),
            destination_addresses=self.parsed_tx.recipient_addresses,
            num_change_outputs=num_change,
            fee_amount=self.parsed_tx.fee,
            has_tokens=bool(self.parsed_tx.sending_tokens),
            network=self.parsed_tx.network,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # "Review details" button pressed - enter sequential review
        return Destination(
            CardanoTxSequentialReviewView,
            view_args=dict(parsed_tx=self.parsed_tx, global_index=0)
        )


class CardanoTxSummaryView(View):
    """
    TX Summary - Shows detailed summary with tokens.
    """

    def __init__(self, parsed_tx: CardanoParsedTx = None):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoTxSummaryScreen

        selected_menu_num = self.run_screen(
            CardanoTxSummaryScreen,
            sending_amount=self.parsed_tx.sending_amount,
            sending_tokens=self.parsed_tx.sending_tokens,
            fee_amount=self.parsed_tx.fee,
            num_recipients=self.parsed_tx.num_recipients,
            change_amount=self.parsed_tx.change_amount,
            network=self.parsed_tx.network,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == 0:  # "View Details"
            return Destination(
                CardanoTxSequentialReviewView,
                view_args=dict(parsed_tx=self.parsed_tx, global_index=0)
            )
        elif selected_menu_num == 1:  # "Sign Transaction"
            return Destination(
                CardanoTxSignView,
                view_args=dict(parsed_tx=self.parsed_tx)
            )


class CardanoTxSignView(View):
    """Sign Transaction - Final confirmation screen."""

    def __init__(self, parsed_tx: CardanoParsedTx):
        super().__init__()
        self.parsed_tx = parsed_tx

    def run(self):
        from seedsigner.gui.screens.tx_review import CardanoTxSignScreen

        selected_menu_num = self.run_screen(
            CardanoTxSignScreen,
            sending_amount=self.parsed_tx.sending_amount,
            fee_amount=self.parsed_tx.fee,
            network=self.parsed_tx.network,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if selected_menu_num == 0:  # Cancel
            return Destination(MainMenuView)
        elif selected_menu_num == 1:  # Sign
            return Destination(MainMenuView, clear_history=True)


# =============================================================================
# Sequential Review - Navigate ALL TX body fields with left/right
# =============================================================================

class CardanoTxSequentialReviewView(View):
    """
    Unified sequential review — navigates through ALL tx body fields
    using left/right, in CBOR key order.

    Outputs use CardanoOutputSequentialScreen (big ADA, address, tokens).
    All other fields use CardanoTxSequentialScreen (content_lines).
    """

    def __init__(self, parsed_tx: CardanoParsedTx, global_index: int = 0):
        super().__init__()
        self.parsed_tx = parsed_tx
        self.global_index = global_index
        self.pages = parsed_tx.build_review_pages()

    def run(self):
        page = self.pages[self.global_index]
        total_pages = len(self.pages)

        has_left = self.global_index > 0
        has_right = True  # Always show — last page right-press goes to sign

        # Build title with section context
        if page.total_in_section > 1:
            title = f"{_SECTION_TITLES[page.section]} {page.item_index + 1}/{page.total_in_section}"
        else:
            title = _SECTION_TITLES[page.section]

        if page.section == "output":
            result = self._render_output(page, title, has_left, has_right, total_pages)
        else:
            result = self._render_generic(page, title, has_left, has_right, total_pages)

        return self._handle_result(result, has_left, total_pages)

    def _render_output(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoOutputSequentialScreen

        output = page.data
        is_change = page.item_index in self.parsed_tx.verified_change_indices

        tokens = None
        ma = output.value.multi_asset
        if ma:
            tokens = {}
            for policy_id, asset_map in ma.items():
                for asset_name, qty in asset_map.items():
                    name = str(asset_name) if str(asset_name) else str(policy_id)[:8]
                    tokens[name] = qty

        return self.run_screen(
            CardanoOutputSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            address=str(output.address),
            amount=output.value.coin,
            tokens=tokens,
            is_change=is_change,
        )

    def _render_generic(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoTxSequentialScreen

        builder = _SECTION_CONTENT_BUILDERS[page.section]
        content_lines = builder(page.data)

        return self.run_screen(
            CardanoTxSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content_lines=content_lines,
        )

    def _handle_result(self, result, has_left, total_pages):
        is_last_page = self.global_index >= total_pages - 1

        if result == RET_CODE__BACK_BUTTON or result == -1:
            return Destination(BackStackView)

        if result == RET_CODE__LEFT_BUTTON and has_left:
            return Destination(
                CardanoTxSequentialReviewView,
                view_args=dict(parsed_tx=self.parsed_tx, global_index=self.global_index - 1),
                skip_current_view=True,
            )

        if result == RET_CODE__RIGHT_BUTTON:
            if is_last_page:
                return Destination(
                    CardanoTxSignView,
                    view_args=dict(parsed_tx=self.parsed_tx),
                )
            return Destination(
                CardanoTxSequentialReviewView,
                view_args=dict(parsed_tx=self.parsed_tx, global_index=self.global_index + 1),
                skip_current_view=True,
            )

        # Center press (0) - shortcut to sign
        if result == 0:
            return Destination(
                CardanoTxSignView,
                view_args=dict(parsed_tx=self.parsed_tx),
            )

        return Destination(BackStackView)

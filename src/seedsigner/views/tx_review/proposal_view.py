"""Governance proposal section review view.

``_PARAM_FIELDS`` lists the ProtocolParamUpdate accessors with their
friendly display names, grouped in order: fees, size limits, staking,
Plutus/script, governance (CIP-1694), and the deprecated pre-Conway fields
(d, extra_entropy, protocol_version). The pool and DRep voting-threshold
accessors are rendered separately by ``_add_voting_thresholds``.
``_LOVELACE_FIELDS`` names the fields whose lovelace values are formatted
as ADA.
"""

from cometa import Bech32, GovernanceActionType, PlutusLanguageVersion

from seedsigner.gui.screens.tx_review import format_ada, Line
from seedsigner.helpers.cardano_utils import format_percent

from .base import BaseSequentialSectionView
from .certificate_view import _format_bech32, _add_anchor


_ACTION_TYPE_NAMES = {
    GovernanceActionType.PARAMETER_CHANGE: "Parameter Change",
    GovernanceActionType.HARD_FORK_INITIATION: "Hard Fork",
    GovernanceActionType.TREASURY_WITHDRAWALS: "Treasury Withdrawal",
    GovernanceActionType.NO_CONFIDENCE: "No Confidence",
    GovernanceActionType.UPDATE_COMMITTEE: "Update Committee",
    GovernanceActionType.NEW_CONSTITUTION: "New Constitution",
    GovernanceActionType.INFO: "Info Action",
}

_PARAM_FIELDS = [
    ("min_fee_a", "Min Fee A"),
    ("min_fee_b", "Min Fee B"),

    ("max_block_body_size", "Max Block Body Size"),
    ("max_tx_size", "Max TX Size"),
    ("max_block_header_size", "Max Block Header Size"),
    ("max_value_size", "Max Value Size"),

    ("key_deposit", "Key Deposit"),
    ("pool_deposit", "Pool Deposit"),
    ("max_epoch", "Max Epoch"),
    ("n_opt", "Desired Pool Count"),
    ("pool_pledge_influence", "Pledge Influence"),
    ("expansion_rate", "Expansion Rate"),
    ("treasury_growth_rate", "Treasury Growth Rate"),
    ("min_pool_cost", "Min Pool Cost"),

    ("ada_per_utxo_byte", "ADA Per UTXO Byte"),
    ("cost_models", "Cost Models"),
    ("execution_costs", "Execution Costs"),
    ("max_tx_ex_units", "Max TX Ex Units"),
    ("max_block_ex_units", "Max Block Ex Units"),
    ("max_collateral_inputs", "Max Collateral Inputs"),
    ("collateral_percentage", "Collateral %"),
    ("ref_script_cost_per_byte", "Ref Script Cost/Byte"),

    ("min_committee_size", "Min Committee Size"),
    ("committee_term_limit", "Committee Term Limit"),
    ("governance_action_validity_period", "Gov Action Validity"),
    ("governance_action_deposit", "Gov Action Deposit"),
    ("drep_deposit", "DRep Deposit"),
    ("drep_inactivity_period", "DRep Inactivity Period"),

    ("d", "Decentralization"),
    ("extra_entropy", "Extra Entropy"),
    ("protocol_version", "Protocol Version"),
]

_LOVELACE_FIELDS = {
    "key_deposit", "pool_deposit", "min_pool_cost", "ada_per_utxo_byte",
    "governance_action_deposit", "drep_deposit",
}

_COEFFICIENT_FIELDS = {"pool_pledge_influence", "ref_script_cost_per_byte"}


class ProposalReviewView(BaseSequentialSectionView):
    section_title = "Proposal"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

        proposal = page.data
        try:
            content = self._build_content(proposal)
        except Exception:
            return self.reject_undisplayable("governance proposal")

        return self.run_screen(
            CardanoContentSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

    def _build_content(self, proposal):
        """Build the display lines for a proposal.

        Order: action type, deposit, reward account, the type-specific
        fields, then the anchor. INFO actions have no type-specific fields.
        """
        lines = []
        at = proposal.action_type
        friendly = _ACTION_TYPE_NAMES.get(at, at.name)

        lines.append(Line.label("Type:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_highlight(friendly))

        lines.append(Line.spacer())
        lines.append(Line.label("Deposit:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_large(format_ada(proposal.deposit)))

        lines.append(Line.spacer())
        reward_bech32 = str(proposal.reward_address)
        fmt, hn, tn = _format_bech32(reward_bech32)
        lines.append(Line.label("Reward Account:"))
        lines.append(Line.spacer_small())
        lines.append(Line.hash(fmt, hn, tn))

        if at == GovernanceActionType.PARAMETER_CHANGE:
            self._add_parameter_change(lines, proposal.to_parameter_change_action())
        elif at == GovernanceActionType.HARD_FORK_INITIATION:
            self._add_hard_fork(lines, proposal.to_hard_fork_initiation_action())
        elif at == GovernanceActionType.TREASURY_WITHDRAWALS:
            self._add_treasury_withdrawals(lines, proposal.to_treasury_withdrawals_action())
        elif at == GovernanceActionType.NO_CONFIDENCE:
            self._add_gov_action_id(lines, proposal.to_no_confidence_action().governance_action_id)
        elif at == GovernanceActionType.UPDATE_COMMITTEE:
            self._add_update_committee(lines, proposal.to_update_committee_action())
        elif at == GovernanceActionType.NEW_CONSTITUTION:
            self._add_new_constitution(lines, proposal.to_constitution_action())

        if proposal.anchor:
            _add_anchor(lines, proposal.anchor)

        return lines

    def _add_gov_action_id(self, lines, gov_id):
        """Add governance action ID if present."""
        if gov_id is None:
            return
        lines.append(Line.spacer())
        gov_bech32 = gov_id.to_bech32()
        fmt, hn, tn = _format_bech32(gov_bech32)
        lines.append(Line.label("Prev Action:"))
        lines.append(Line.spacer_small())
        lines.append(Line.hash(fmt, hn, tn))

    def _add_parameter_change(self, lines, action):
        """Render a parameter change action listing every changed parameter.

        _PARAM_FIELDS plus the voting threshold sections cover every
        accessor cometa's ProtocolParamUpdate exposes, so no change the
        library can surface is silently omitted. cometa provides no way
        to enumerate update keys it does not expose through accessors; a
        key unknown to cometa can only be caught by its CBOR parser
        failing, which render() turns into a rejection.
        """
        self._add_gov_action_id(lines, action.governance_action_id)

        if action.policy_hash:
            lines.append(Line.spacer())
            policy_bech32 = Bech32.encode("script", action.policy_hash.to_bytes())
            fmt, hn, tn = _format_bech32(policy_bech32)
            lines.append(Line.label("Policy:"))
            lines.append(Line.spacer_small())
            lines.append(Line.hash(fmt, hn, tn))

        ppu = action.protocol_param_update
        lines.append(Line.spacer())
        lines.append(Line.label("Changes:"))

        for field_name, friendly_name in _PARAM_FIELDS:
            val = getattr(ppu, field_name, None)
            if val is None:
                continue
            for line in self._format_param_lines(field_name, friendly_name, val):
                lines.append(Line.spacer_small())
                lines.append(Line.value_highlight(line))

        self._add_voting_thresholds(lines, ppu)

    def _format_param_lines(self, field_name, friendly_name, val):
        """Format a changed parameter as one or more display lines.

        execution_costs expands into one coefficient line per price
        rational. cost_models is too large to show in full on screen, so
        it renders as a digest naming the Plutus languages whose cost
        model the proposal updates.
        """
        if field_name == "execution_costs":
            mem = f"{float(val.memory_prices):g}"
            steps = f"{float(val.steps_prices):g}"
            return [f"Mem Price: {mem}", f"Step Price: {steps}"]
        if field_name == "cost_models":
            langs = [f"Plutus {v.name}" for v in PlutusLanguageVersion if val.has(v)]
            detail = ", ".join(langs) if langs else "updated"
            return [f"{friendly_name}: {detail}"]
        val_str = self._format_param_value(field_name, val)
        return [f"{friendly_name}: {val_str}"]

    def _format_param_value(self, field_name, val):
        """Format a protocol parameter value for display.

        Rational fields in _COEFFICIENT_FIELDS are plain coefficients, such
        as multipliers or per-byte costs, shown as decimals; the remaining
        rationals are rates shown as percentages.
        """
        if field_name in _LOVELACE_FIELDS:
            return format_ada(val)
        if hasattr(val, "to_float"):
            if field_name in _COEFFICIENT_FIELDS:
                return f"{float(val):g}"
            return format_percent(val)
        if hasattr(val, "memory") and hasattr(val, "cpu_steps"):
            return f"mem:{val.memory:,} cpu:{val.cpu_steps:,}"
        if hasattr(val, "major") and hasattr(val, "minor"):
            return f"{val.major}.{val.minor}"
        if hasattr(val, "to_hex"):
            return val.to_hex()
        return str(val)

    def _add_voting_thresholds(self, lines, ppu):
        """Add DRep and pool voting thresholds if changed."""
        drep = getattr(ppu, "drep_voting_thresholds", None)
        if drep:
            lines.append(Line.spacer())
            lines.append(Line.label("DRep Thresholds:"))
            for name, friendly in [
                ("motion_no_confidence", "No Confidence"),
                ("committee_normal", "Committee Normal"),
                ("committee_no_confidence", "Committee No Conf."),
                ("update_constitution", "Constitution"),
                ("hard_fork_initiation", "Hard Fork"),
                ("pp_network_group", "PP Network"),
                ("pp_economic_group", "PP Economic"),
                ("pp_technical_group", "PP Technical"),
                ("pp_governance_group", "PP Governance"),
                ("treasury_withdrawal", "Treasury"),
            ]:
                val = getattr(drep, name, None)
                if val is not None:
                    pct_str = format_percent(val)
                    lines.append(Line.spacer_small())
                    lines.append(Line.value_highlight(f"{friendly}: {pct_str}"))

        pool = getattr(ppu, "pool_voting_thresholds", None)
        if pool:
            lines.append(Line.spacer())
            lines.append(Line.label("Pool Thresholds:"))
            for name, friendly in [
                ("motion_no_confidence", "No Confidence"),
                ("committee_normal", "Committee Normal"),
                ("committee_no_confidence", "Committee No Conf."),
                ("hard_fork_initiation", "Hard Fork"),
                ("security_relevant_param", "Security Param"),
            ]:
                val = getattr(pool, name, None)
                if val is not None:
                    pct_str = format_percent(val)
                    lines.append(Line.spacer_small())
                    lines.append(Line.value_highlight(f"{friendly}: {pct_str}"))

    def _add_hard_fork(self, lines, action):
        self._add_gov_action_id(lines, action.governance_action_id)

        pv = action.protocol_version
        lines.append(Line.spacer())
        lines.append(Line.label("Target Version:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_highlight(f"{pv.major}.{pv.minor}"))

    def _add_treasury_withdrawals(self, lines, action):
        if action.policy_hash:
            lines.append(Line.spacer())
            policy_bech32 = Bech32.encode("script", action.policy_hash.to_bytes())
            fmt, hn, tn = _format_bech32(policy_bech32)
            lines.append(Line.label("Policy:"))
            lines.append(Line.spacer_small())
            lines.append(Line.hash(fmt, hn, tn))

        lines.append(Line.spacer())
        lines.append(Line.label(f"Withdrawals ({len(action.withdrawals)}):"))

        for addr, amount in action.withdrawals.items():
            addr_bech32 = str(addr)
            fmt, hn, tn = _format_bech32(addr_bech32)
            lines.append(Line.spacer())
            lines.append(Line.value_large(format_ada(amount)))
            lines.append(Line.spacer_small())
            lines.append(Line.hash(fmt, hn, tn))

    def _add_update_committee(self, lines, action):
        self._add_gov_action_id(lines, action.governance_action_id)

        q_str = format_percent(action.quorum)
        lines.append(Line.spacer())
        lines.append(Line.label("Quorum:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_highlight(q_str))

        if len(action.members_to_be_added) > 0:
            lines.append(Line.spacer())
            lines.append(Line.label(f"Add ({len(action.members_to_be_added)}):"))
            for cred, epoch in action.members_to_be_added.items():
                prefix = "cc_cold_vkh" if cred.is_key_hash else "cc_cold"
                bech32_str = Bech32.encode(prefix, cred.hash_bytes)
                fmt, hn, tn = _format_bech32(bech32_str)
                lines.append(Line.spacer())
                lines.append(Line.hash(fmt, hn, tn))
                lines.append(Line.spacer_small())
                lines.append(Line.value_highlight(f"Term: epoch {epoch}"))

        if len(action.members_to_be_removed) > 0:
            lines.append(Line.spacer())
            lines.append(Line.label(f"Remove ({len(action.members_to_be_removed)}):"))
            for cred in action.members_to_be_removed:
                prefix = "cc_cold_vkh" if cred.is_key_hash else "cc_cold"
                bech32_str = Bech32.encode(prefix, cred.hash_bytes)
                fmt, hn, tn = _format_bech32(bech32_str)
                lines.append(Line.spacer())
                lines.append(Line.hash(fmt, hn, tn))

    def _add_new_constitution(self, lines, action):
        self._add_gov_action_id(lines, action.governance_action_id)

        constitution = action.constitution

        lines.append(Line.spacer())
        lines.append(Line.label("Constitution URL:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_highlight(str(constitution.anchor.url)))
        anchor_hash = constitution.anchor.hash_hex
        if anchor_hash:
            lines.append(Line.spacer())
            lines.append(Line.label("Constitution Hash:"))
            lines.append(Line.spacer_small())
            from .certificate_view import _format_hex_display
            fmt = _format_hex_display(anchor_hash)
            lines.append(Line.hash(fmt, 8, 8))

        if constitution.script_hash:
            lines.append(Line.spacer())
            script_bech32 = Bech32.encode("script", constitution.script_hash.to_bytes())
            fmt, hn, tn = _format_bech32(script_bech32)
            lines.append(Line.label("Script:"))
            lines.append(Line.spacer_small())
            lines.append(Line.hash(fmt, hn, tn))

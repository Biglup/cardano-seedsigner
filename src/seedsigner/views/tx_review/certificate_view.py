"""Certificate section review view."""

from cometa import Bech32, CertificateType

from seedsigner.gui.screens.tx_review import format_ada, Line
from seedsigner.helpers.cardano_utils import format_percent

from .base import BaseSequentialSectionView

_CERT_TYPE_NAMES = {
    "STAKE_REGISTRATION": "Stake Registration",
    "STAKE_DEREGISTRATION": "Stake Deregistration",
    "STAKE_DELEGATION": "Stake Delegation",
    "POOL_REGISTRATION": "Pool Registration",
    "POOL_RETIREMENT": "Pool Retirement",
    "GENESIS_KEY_DELEGATION": "Genesis Key Delegation",
    "MOVE_INSTANTANEOUS_REWARDS": "MIR Certificate",
    "REGISTRATION": "Registration",
    "UNREGISTRATION": "Unregistration",
    "VOTE_DELEGATION": "Vote Delegation",
    "STAKE_VOTE_DELEGATION": "Stake & Vote Delegation",
    "STAKE_REGISTRATION_DELEGATION": "Stake Reg. & Delegation",
    "VOTE_REGISTRATION_DELEGATION": "Vote Reg. & Delegation",
    "STAKE_VOTE_REGISTRATION_DELEGATION": "Stake & Vote Reg. & Del.",
    "AUTH_COMMITTEE_HOT": "Authorize Committee Hot",
    "RESIGN_COMMITTEE_COLD": "Resign Committee Cold",
    "DREP_REGISTRATION": "DRep Registration",
    "DREP_UNREGISTRATION": "DRep Unregistration",
    "UPDATE_DREP": "DRep Update",
}

_TAIL_HIGHLIGHT = 6


def _format_hex_display(hex_str, highlight_n=8):
    """Format a hex hash with spaces for highlighting (byte-aligned)."""
    if len(hex_str) > 2 * highlight_n:
        return f"{hex_str[:highlight_n]} {hex_str[highlight_n:-highlight_n]} {hex_str[-highlight_n:]}"
    return hex_str


def _add_anchor(lines, anchor):
    """Add anchor URL and hash entries to content lines."""
    lines.append(Line.spacer())
    lines.append(Line.label("Anchor URL:"))
    lines.append(Line.spacer_small())
    lines.append(Line.value_highlight(str(anchor.url)))
    anchor_hash = anchor.hash_hex
    if anchor_hash:
        lines.append(Line.spacer())
        lines.append(Line.label("Anchor Hash:"))
        lines.append(Line.spacer_small())
        fmt = _format_hex_display(anchor_hash)
        lines.append(Line.hash(fmt, 8, 8))


def _format_bech32(bech32_str):
    """Format a bech32 string with spaces for display highlighting.

    Highlights the prefix (up to and including '1') plus 4 data chars at the
    start, and _TAIL_HIGHLIGHT chars at the end.

    Returns (formatted_str, head_n, tail_n).
    """
    sep = bech32_str.find("1")
    head_n = sep + 1 + 4 if sep >= 0 else 7
    tail_n = _TAIL_HIGHLIGHT
    if len(bech32_str) > head_n + tail_n:
        return (
            f"{bech32_str[:head_n]} {bech32_str[head_n:-tail_n]} {bech32_str[-tail_n:]}",
            head_n,
            tail_n,
        )
    return bech32_str, head_n, tail_n


class CertificateReviewView(BaseSequentialSectionView):
    """Review page for one certificate (Conway CDDL body key 4).

    Covers the pre-Conway staking and pool certificates and the Conway
    governance certificates (DRep, committee, vote delegation).
    """
    section_title = "Certificate"

    def render(self, page, title, has_left, has_right, total_pages):
        """Render the certificate, rejecting the transaction if it cannot be displayed."""
        from seedsigner.gui.screens.tx_review import CardanoContentSequentialScreen

        cert = page.data
        try:
            content = self._build_content(cert)
        except Exception:
            return self.reject_undisplayable("certificate")

        return self.run_screen(
            CardanoContentSequentialScreen,
            title=title,
            page_num=self.global_index + 1,
            total_pages=total_pages,
            has_left=has_left,
            has_right=has_right,
            content=content,
        )

    def _build_content(self, cert):
        ct = cert.cert_type
        friendly_name = _CERT_TYPE_NAMES.get(ct.name, ct.name)
        lines = []

        lines.append(Line.label("Type:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_highlight(friendly_name))

        builder = self._CERT_BUILDERS.get(ct)
        if builder is None:
            lines.append(Line.spacer())
            lines.append(Line.value_text(f"Type value: {ct.value}"))
        else:
            builder(self, lines, cert)

        return lines

    def _build_stake_registration(self, lines, cert):
        """Stake credential of a pre-Conway stake registration."""
        self._add_stake_credential(lines, cert.to_stake_registration().credential)

    def _build_stake_deregistration(self, lines, cert):
        """Stake credential of a pre-Conway stake deregistration."""
        self._add_stake_credential(lines, cert.to_stake_deregistration().credential)

    def _build_stake_delegation(self, lines, cert):
        """Stake credential and target pool of a stake delegation."""
        sd = cert.to_stake_delegation()
        self._add_stake_credential(lines, sd.credential)
        self._add_pool(lines, sd.pool_key_hash)

    def _build_pool_registration(self, lines, cert):
        """Full pool parameters: operator, pledge, cost, margin, VRF key,
        reward account, owners, relays, and optional metadata."""
        pr = cert.to_pool_registration()
        p = pr.params
        self._add_pool(lines, p.operator_key_hash)
        self._add_amount_field(lines, "Pledge:", p.pledge)
        self._add_amount_field(lines, "Cost:", p.cost)
        margin_str = format_percent(p.margin)
        lines.append(Line.spacer())
        lines.append(Line.label("Margin:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_highlight(margin_str))
        self._add_bech32_hash(lines, "VRF Key:", p.vrf_vk_hash, "vrf_vk")
        self._add_bech32_display(lines, "Reward Account:", str(p.reward_account))
        if len(p.owners) > 0:
            lines.append(Line.spacer())
            lines.append(Line.label(f"Owners ({len(p.owners)}):"))
            for owner in p.owners:
                bech32_str = Bech32.encode("stake_vkh", owner.to_bytes())
                fmt, hn, tn = _format_bech32(bech32_str)
                lines.append(Line.spacer())
                lines.append(Line.hash(fmt, hn, tn))
        if len(p.relays) > 0:
            lines.append(Line.spacer())
            lines.append(Line.label(f"Relays ({len(p.relays)}):"))
            for relay in p.relays:
                lines.append(Line.spacer())
                self._add_relay(lines, relay)
        if p.metadata:
            lines.append(Line.spacer())
            lines.append(Line.label("Metadata URL:"))
            lines.append(Line.spacer_small())
            lines.append(Line.value_highlight(str(p.metadata.url)))
            lines.append(Line.spacer())
            lines.append(Line.label("Metadata Hash:"))
            lines.append(Line.spacer_small())
            meta_hash = p.metadata.hash.to_hex()
            fmt = _format_hex_display(meta_hash)
            lines.append(Line.hash(fmt, 8, 8))

    def _build_pool_retirement(self, lines, cert):
        """Pool and the epoch at which it retires."""
        pr = cert.to_pool_retirement()
        self._add_pool(lines, pr.pool_key_hash)
        lines.append(Line.spacer())
        lines.append(Line.label("Epoch:"))
        lines.append(Line.spacer_small())
        lines.append(Line.value_highlight(str(pr.epoch)))

    def _build_registration(self, lines, cert):
        """Stake credential and deposit of a Conway registration."""
        r = cert.to_registration()
        self._add_stake_credential(lines, r.credential)
        self._add_amount_field(lines, "Deposit:", r.deposit)

    def _build_unregistration(self, lines, cert):
        """Stake credential and returned deposit of a Conway unregistration."""
        u = cert.to_unregistration()
        self._add_stake_credential(lines, u.credential)
        self._add_amount_field(lines, "Deposit:", u.deposit)

    def _build_vote_delegation(self, lines, cert):
        """Stake credential and the DRep it delegates its vote to."""
        vd = cert.to_vote_delegation()
        self._add_stake_credential(lines, vd.credential)
        self._add_drep(lines, vd.drep)

    def _build_stake_vote_delegation(self, lines, cert):
        """Stake credential delegating to both a pool and a DRep."""
        svd = cert.to_stake_vote_delegation()
        self._add_stake_credential(lines, svd.credential)
        self._add_pool(lines, svd.pool_key_hash)
        self._add_drep(lines, svd.drep)

    def _build_stake_registration_delegation(self, lines, cert):
        """Registration combined with pool delegation and its deposit."""
        srd = cert.to_stake_registration_delegation()
        self._add_stake_credential(lines, srd.credential)
        self._add_pool(lines, srd.pool_key_hash)
        self._add_amount_field(lines, "Deposit:", srd.deposit)

    def _build_vote_registration_delegation(self, lines, cert):
        """Registration combined with vote delegation and its deposit."""
        vrd = cert.to_vote_registration_delegation()
        self._add_stake_credential(lines, vrd.credential)
        self._add_drep(lines, vrd.drep)
        self._add_amount_field(lines, "Deposit:", vrd.deposit)

    def _build_stake_vote_registration_delegation(self, lines, cert):
        """Registration combined with pool and vote delegation and its deposit."""
        svrd = cert.to_stake_vote_registration_delegation()
        self._add_stake_credential(lines, svrd.credential)
        self._add_pool(lines, svrd.pool_key_hash)
        self._add_drep(lines, svrd.drep)
        self._add_amount_field(lines, "Deposit:", svrd.deposit)

    def _build_auth_committee_hot(self, lines, cert):
        """Committee cold and hot credentials being authorized."""
        ach = cert.to_auth_committee_hot()
        self._add_bech32_credential(lines, "Cold:", ach.committee_cold_credential, "cc_cold")
        self._add_bech32_credential(lines, "Hot:", ach.committee_hot_credential, "cc_hot")

    def _build_resign_committee_cold(self, lines, cert):
        """Resigning committee cold credential and optional anchor."""
        rcc = cert.to_resign_committee_cold()
        self._add_bech32_credential(lines, "Cold:", rcc.committee_cold_credential, "cc_cold")
        if rcc.anchor:
            _add_anchor(lines, rcc.anchor)

    def _build_drep_registration(self, lines, cert):
        """DRep credential, deposit, and optional anchor."""
        rd = cert.to_register_drep()
        self._add_drep_credential(lines, rd.credential)
        self._add_amount_field(lines, "Deposit:", rd.deposit)
        if rd.anchor:
            _add_anchor(lines, rd.anchor)

    def _build_drep_unregistration(self, lines, cert):
        """DRep credential and returned deposit."""
        ud = cert.to_unregister_drep()
        self._add_drep_credential(lines, ud.credential)
        self._add_amount_field(lines, "Deposit:", ud.deposit)

    def _build_update_drep(self, lines, cert):
        """DRep credential and optional updated anchor."""
        ud = cert.to_update_drep()
        self._add_drep_credential(lines, ud.credential)
        if ud.anchor:
            _add_anchor(lines, ud.anchor)

    _CERT_BUILDERS = {
        CertificateType.STAKE_REGISTRATION: _build_stake_registration,
        CertificateType.STAKE_DEREGISTRATION: _build_stake_deregistration,
        CertificateType.STAKE_DELEGATION: _build_stake_delegation,
        CertificateType.POOL_REGISTRATION: _build_pool_registration,
        CertificateType.POOL_RETIREMENT: _build_pool_retirement,
        CertificateType.REGISTRATION: _build_registration,
        CertificateType.UNREGISTRATION: _build_unregistration,
        CertificateType.VOTE_DELEGATION: _build_vote_delegation,
        CertificateType.STAKE_VOTE_DELEGATION: _build_stake_vote_delegation,
        CertificateType.STAKE_REGISTRATION_DELEGATION: _build_stake_registration_delegation,
        CertificateType.VOTE_REGISTRATION_DELEGATION: _build_vote_registration_delegation,
        CertificateType.STAKE_VOTE_REGISTRATION_DELEGATION: _build_stake_vote_registration_delegation,
        CertificateType.AUTH_COMMITTEE_HOT: _build_auth_committee_hot,
        CertificateType.RESIGN_COMMITTEE_COLD: _build_resign_committee_cold,
        CertificateType.DREP_REGISTRATION: _build_drep_registration,
        CertificateType.DREP_UNREGISTRATION: _build_drep_unregistration,
        CertificateType.UPDATE_DREP: _build_update_drep,
    }

    def _add_bech32_display(self, lines, label, bech32_str):
        """Add a bech32 identifier with label and prefix-aware highlighting."""
        fmt, hn, tn = _format_bech32(bech32_str)
        lines.append(Line.spacer())
        lines.append(Line.label(label))
        lines.append(Line.spacer_small())
        lines.append(Line.hash(fmt, hn, tn))

    def _add_credential_display(self, lines, base_label, bech32_str, credential):
        """Display a credential with its ownership badge.

        Key-hash credentials are checked against the key hashes derived
        on-device from the request's declared paths: a match is proof the
        credential is the wallet's ("Own Key" badge), otherwise it is
        badged "Unknown Key" (ownership could not be verified; it may
        equally be a third party's key or an undeclared own key). Script
        credentials can't be proven either way and stay unbadged.
        """
        self._add_bech32_display(lines, f"{base_label}:", bech32_str)
        if not credential.is_key_hash:
            return

        lines.append(Line.spacer_small())
        if credential.hash_bytes in self.parsed_tx.owned_key_hashes:
            lines.append(Line.verified("Own Key"))
        else:
            lines.append(Line.foreign("Unknown Key"))

    def _add_stake_credential(self, lines, credential):
        """Display a stake credential (key hash or script) with its ownership badge."""
        prefix = "stake_vkh" if credential.is_key_hash else "script"
        bech32_str = Bech32.encode(prefix, credential.hash_bytes)
        self._add_credential_display(lines, "Credential", bech32_str, credential)

    def _add_drep_credential(self, lines, credential):
        """Encode a DRep credential using CIP-129 format."""
        from cometa import DRep as DRepCls, DRepType
        dt = DRepType.KEY_HASH if credential.is_key_hash else DRepType.SCRIPT_HASH
        drep = DRepCls.new(dt, credential)
        self._add_credential_display(lines, "DRep ID", str(drep), credential)

    def _add_pool(self, lines, pool_key_hash):
        """Display a stake pool id as a ``pool1...`` bech32 identifier."""
        bech32_str = Bech32.encode("pool", pool_key_hash.to_bytes())
        self._add_bech32_display(lines, "Pool:", bech32_str)

    def _add_bech32_hash(self, lines, label, hash_obj, prefix):
        """Encode a hash under ``prefix`` and display it as a labelled bech32 value."""
        bech32_str = Bech32.encode(prefix, hash_obj.to_bytes())
        self._add_bech32_display(lines, label, bech32_str)

    def _add_bech32_credential(self, lines, label, credential, prefix):
        """Display a credential encoded under ``prefix`` with its ownership badge."""
        bech32_str = Bech32.encode(prefix, credential.hash_bytes)
        self._add_credential_display(lines, label.rstrip(":"), bech32_str, credential)

    def _add_amount_field(self, lines, label, lovelace):
        """Display a labelled lovelace amount formatted as ADA."""
        lines.append(Line.spacer())
        lines.append(Line.label(label))
        lines.append(Line.spacer_small())
        lines.append(Line.value_large(format_ada(lovelace)))

    def _add_relay(self, lines, relay):
        """Display a pool relay: host address with port, DNS name, or multi-host name."""
        from cometa import RelayType
        rt = relay.relay_type
        lines.append(Line.spacer_small())
        if rt == RelayType.SINGLE_HOST_ADDRESS:
            r = relay.to_single_host_addr()
            addr = ""
            if r.ipv4:
                addr = r.ipv4.to_string()
            elif r.ipv6:
                addr = r.ipv6.to_string()
            if r.port is not None:
                addr = f"{addr}:{r.port}" if addr else f"port {r.port}"
            lines.append(Line.value_highlight(addr or "(no address)"))
        elif rt == RelayType.SINGLE_HOST_NAME:
            r = relay.to_single_host_name()
            text = r.dns
            if r.port is not None:
                text += f":{r.port}"
            lines.append(Line.value_highlight(text))
        elif rt == RelayType.MULTI_HOST_NAME:
            r = relay.to_multi_host_name()
            lines.append(Line.value_highlight(r.dns))

    def _add_drep(self, lines, drep):
        """Display a vote-delegation target: Abstain, No Confidence, or a ``drep...`` id."""
        from cometa import DRepType
        lines.append(Line.spacer())
        lines.append(Line.label("DRep:"))
        lines.append(Line.spacer_small())
        dt = drep.drep_type
        if dt == DRepType.ABSTAIN:
            lines.append(Line.value_highlight("Abstain"))
        elif dt == DRepType.NO_CONFIDENCE:
            lines.append(Line.value_highlight("No Confidence"))
        else:
            drep_str = str(drep)
            fmt, hn, tn = _format_bech32(drep_str)
            lines.append(Line.hash(fmt, hn, tn))

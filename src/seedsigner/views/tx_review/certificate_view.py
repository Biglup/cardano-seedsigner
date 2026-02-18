"""Certificate section review view."""

from cometa import Bech32

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView

# Friendly names for certificate types
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
    lines.append(("spacer", ""))
    lines.append(("label", "Anchor URL:"))
    lines.append(("spacer_small", ""))
    lines.append(("value_text", str(anchor.url)))
    anchor_hash = anchor.hash_hex
    if anchor_hash:
        lines.append(("spacer", ""))
        lines.append(("label", "Anchor Hash:"))
        lines.append(("spacer_small", ""))
        fmt = _format_hex_display(anchor_hash)
        lines.append(("hash_display", fmt, 8, 8))


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
    section_title = "Certificate"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoCertificateSequentialScreen

        cert = page.data
        content = self._build_content(cert)

        return self.run_screen(
            CardanoCertificateSequentialScreen,
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

        # Certificate type — blue, prominent
        lines.append(("label", "Type:"))
        lines.append(("spacer_small", ""))
        lines.append(("value_highlight", friendly_name))

        try:
            if ct.name == "STAKE_REGISTRATION":
                self._add_stake_credential(lines, cert.to_stake_registration().credential)

            elif ct.name == "STAKE_DEREGISTRATION":
                self._add_stake_credential(lines, cert.to_stake_deregistration().credential)

            elif ct.name == "STAKE_DELEGATION":
                sd = cert.to_stake_delegation()
                self._add_stake_credential(lines, sd.credential)
                self._add_pool(lines, sd.pool_key_hash)

            elif ct.name == "POOL_REGISTRATION":
                pr = cert.to_pool_registration()
                p = pr.params
                self._add_pool(lines, p.operator_key_hash)
                self._add_amount_field(lines, "Pledge:", p.pledge)
                self._add_amount_field(lines, "Cost:", p.cost)
                margin_pct = float(p.margin) * 100
                if margin_pct == int(margin_pct):
                    margin_str = f"{int(margin_pct)}%"
                else:
                    margin_str = f"{margin_pct:.2f}%"
                lines.append(("spacer", ""))
                lines.append(("label", "Margin:"))
                lines.append(("spacer_small", ""))
                lines.append(("value_text", margin_str))
                self._add_bech32_hash(lines, "VRF Key:", p.vrf_vk_hash, "vrf_vk")
                self._add_bech32_display(lines, "Reward Account:", str(p.reward_account))
                if len(p.owners) > 0:
                    lines.append(("spacer", ""))
                    lines.append(("label", f"Owners ({len(p.owners)}):"))
                    for owner in p.owners:
                        bech32_str = Bech32.encode("stake_vkh", owner.to_bytes())
                        fmt, hn, tn = _format_bech32(bech32_str)
                        lines.append(("spacer", ""))
                        lines.append(("hash_display", fmt, hn, tn))
                if len(p.relays) > 0:
                    lines.append(("spacer", ""))
                    lines.append(("label", f"Relays ({len(p.relays)}):"))
                    for relay in p.relays:
                        lines.append(("spacer", ""))
                        self._add_relay(lines, relay)
                if p.metadata:
                    lines.append(("spacer", ""))
                    lines.append(("label", "Metadata URL:"))
                    lines.append(("spacer_small", ""))
                    lines.append(("value_text", str(p.metadata.url)))

            elif ct.name == "POOL_RETIREMENT":
                pr = cert.to_pool_retirement()
                self._add_pool(lines, pr.pool_key_hash)
                lines.append(("spacer", ""))
                lines.append(("label", "Epoch:"))
                lines.append(("spacer_small", ""))
                lines.append(("value_highlight", str(pr.epoch)))

            elif ct.name == "REGISTRATION":
                r = cert.to_registration()
                self._add_stake_credential(lines, r.credential)
                self._add_amount_field(lines, "Deposit:", r.deposit)

            elif ct.name == "UNREGISTRATION":
                u = cert.to_unregistration()
                self._add_stake_credential(lines, u.credential)
                self._add_amount_field(lines, "Deposit:", u.deposit)

            elif ct.name == "VOTE_DELEGATION":
                vd = cert.to_vote_delegation()
                self._add_stake_credential(lines, vd.credential)
                self._add_drep(lines, vd.drep)

            elif ct.name == "STAKE_VOTE_DELEGATION":
                svd = cert.to_stake_vote_delegation()
                self._add_stake_credential(lines, svd.credential)
                self._add_pool(lines, svd.pool_key_hash)
                self._add_drep(lines, svd.drep)

            elif ct.name == "STAKE_REGISTRATION_DELEGATION":
                srd = cert.to_stake_registration_delegation()
                self._add_stake_credential(lines, srd.credential)
                self._add_pool(lines, srd.pool_key_hash)
                self._add_amount_field(lines, "Deposit:", srd.deposit)

            elif ct.name == "VOTE_REGISTRATION_DELEGATION":
                vrd = cert.to_vote_registration_delegation()
                self._add_stake_credential(lines, vrd.credential)
                self._add_drep(lines, vrd.drep)
                self._add_amount_field(lines, "Deposit:", vrd.deposit)

            elif ct.name == "STAKE_VOTE_REGISTRATION_DELEGATION":
                svrd = cert.to_stake_vote_registration_delegation()
                self._add_stake_credential(lines, svrd.credential)
                self._add_pool(lines, svrd.pool_key_hash)
                self._add_drep(lines, svrd.drep)
                self._add_amount_field(lines, "Deposit:", svrd.deposit)

            elif ct.name == "AUTH_COMMITTEE_HOT":
                ach = cert.to_auth_committee_hot()
                self._add_bech32_credential(lines, "Cold:", ach.committee_cold_credential, "cc_cold")
                self._add_bech32_credential(lines, "Hot:", ach.committee_hot_credential, "cc_hot")

            elif ct.name == "RESIGN_COMMITTEE_COLD":
                rcc = cert.to_resign_committee_cold()
                self._add_bech32_credential(lines, "Cold:", rcc.committee_cold_credential, "cc_cold")
                if rcc.anchor:
                    _add_anchor(lines, rcc.anchor)

            elif ct.name == "DREP_REGISTRATION":
                rd = cert.to_register_drep()
                self._add_drep_credential(lines, rd.credential)
                self._add_amount_field(lines, "Deposit:", rd.deposit)
                if rd.anchor:
                    _add_anchor(lines, rd.anchor)

            elif ct.name == "DREP_UNREGISTRATION":
                ud = cert.to_unregister_drep()
                self._add_drep_credential(lines, ud.credential)
                self._add_amount_field(lines, "Deposit:", ud.deposit)

            elif ct.name == "UPDATE_DREP":
                ud = cert.to_update_drep()
                self._add_drep_credential(lines, ud.credential)
                if ud.anchor:
                    _add_anchor(lines, ud.anchor)

            else:
                lines.append(("spacer", ""))
                lines.append(("value_text", f"Type value: {ct.value}"))

        except Exception:
            lines.append(("spacer", ""))
            lines.append(("value_text", "(parse error)"))

        return lines

    def _add_bech32_display(self, lines, label, bech32_str):
        """Add a bech32 identifier with label and prefix-aware highlighting."""
        fmt, hn, tn = _format_bech32(bech32_str)
        lines.append(("spacer", ""))
        lines.append(("label", label))
        lines.append(("spacer_small", ""))
        lines.append(("hash_display", fmt, hn, tn))

    def _add_stake_credential(self, lines, credential):
        prefix = "stake_vkh" if credential.is_key_hash else "script"
        bech32_str = Bech32.encode(prefix, credential.hash_bytes)
        self._add_bech32_display(lines, "Credential:", bech32_str)

    def _add_drep_credential(self, lines, credential):
        """Encode a DRep credential using CIP-129 format."""
        from cometa import DRep as DRepCls, DRepType
        dt = DRepType.KEY_HASH if credential.is_key_hash else DRepType.SCRIPT_HASH
        drep = DRepCls.new(dt, credential)
        self._add_bech32_display(lines, "DRep ID:", str(drep))

    def _add_pool(self, lines, pool_key_hash):
        bech32_str = Bech32.encode("pool", pool_key_hash.to_bytes())
        self._add_bech32_display(lines, "Pool:", bech32_str)

    def _add_bech32_hash(self, lines, label, hash_obj, prefix):
        bech32_str = Bech32.encode(prefix, hash_obj.to_bytes())
        self._add_bech32_display(lines, label, bech32_str)

    def _add_bech32_credential(self, lines, label, credential, prefix):
        bech32_str = Bech32.encode(prefix, credential.hash_bytes)
        self._add_bech32_display(lines, label, bech32_str)

    def _add_amount_field(self, lines, label, lovelace):
        lines.append(("spacer", ""))
        lines.append(("label", label))
        lines.append(("spacer_small", ""))
        lines.append(("value_large", format_ada(lovelace)))

    def _add_relay(self, lines, relay):
        from cometa import RelayType
        rt = relay.relay_type
        lines.append(("spacer_small", ""))
        if rt == RelayType.SINGLE_HOST_ADDRESS:
            r = relay.to_single_host_addr()
            addr = ""
            if r.ipv4:
                addr = r.ipv4.to_string()
            elif r.ipv6:
                addr = r.ipv6.to_string()
            if r.port is not None:
                addr = f"{addr}:{r.port}" if addr else f"port {r.port}"
            lines.append(("value_text", addr or "(no address)"))
        elif rt == RelayType.SINGLE_HOST_NAME:
            r = relay.to_single_host_name()
            text = r.dns
            if r.port is not None:
                text += f":{r.port}"
            lines.append(("value_text", text))
        elif rt == RelayType.MULTI_HOST_NAME:
            r = relay.to_multi_host_name()
            lines.append(("value_text", r.dns))

    def _add_drep(self, lines, drep):
        from cometa import DRepType
        lines.append(("spacer", ""))
        lines.append(("label", "DRep:"))
        lines.append(("spacer_small", ""))
        dt = drep.drep_type
        if dt == DRepType.ABSTAIN:
            lines.append(("value_highlight", "Abstain"))
        elif dt == DRepType.NO_CONFIDENCE:
            lines.append(("value_highlight", "No Confidence"))
        else:
            drep_str = str(drep)
            fmt, hn, tn = _format_bech32(drep_str)
            lines.append(("hash_display", fmt, hn, tn))

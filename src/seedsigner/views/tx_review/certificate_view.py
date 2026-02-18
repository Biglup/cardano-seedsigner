"""Certificate section review view."""

from seedsigner.gui.screens.tx_review import format_ada

from .base import BaseSequentialSectionView


class CertificateReviewView(BaseSequentialSectionView):
    section_title = "Certificate"

    def render(self, page, title, has_left, has_right, total_pages):
        content_lines = self._build_content_lines(page.data)
        return self.render_generic(content_lines, title, has_left, has_right, total_pages)

    def _build_content_lines(self, cert) -> list[str]:
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

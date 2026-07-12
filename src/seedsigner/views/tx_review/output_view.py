"""Output section review view."""

from seedsigner.helpers.cardano_utils import asset_fingerprint

from .base import BaseSequentialSectionView


def _extract_datum_info(output):
    """Extract datum type and hex preview from a transaction output."""
    from cometa import DatumType, CborWriter
    datum = output.datum
    if datum is None:
        return None, None
    dt = datum.datum_type
    if dt == DatumType.DATA_HASH:
        return "Hash", datum.data_hash_hex
    else:
        inline = datum.get_inline_data()
        w = CborWriter()
        inline.to_cbor(w)
        return "Inline", w.to_hex()


def _extract_script_ref_info(output):
    """Extract script language from a transaction output's reference script."""
    from cometa import ScriptLanguage
    script = output.script_ref
    if script is None:
        return None
    lang = script.language
    lang_map = {
        ScriptLanguage.NATIVE: "Native Script",
        ScriptLanguage.PLUTUS_V1: "Plutus V1",
        ScriptLanguage.PLUTUS_V2: "Plutus V2",
        ScriptLanguage.PLUTUS_V3: "Plutus V3",
    }
    return lang_map.get(lang, "Unknown")


class OutputReviewView(BaseSequentialSectionView):
    """Review page for one transaction output (Conway CDDL body key 1).

    Shows the address, ADA amount, native tokens, datum and reference script,
    labelling the address as this wallet's own change or a foreign destination.
    """
    section_title = "Output"

    def render(self, page, title, has_left, has_right, total_pages):
        from seedsigner.gui.screens.tx_review import CardanoOutputSequentialScreen

        output = page.data
        is_change = page.item_index in self.parsed_tx.verified_change_indices

        tokens = None
        ma = output.value.multi_asset
        if ma:
            tokens = {}
            for policy_id, asset_map in ma.items():
                for asset_name, qty in asset_map.items():
                    fingerprint = asset_fingerprint(policy_id, asset_name)
                    tokens[fingerprint] = qty

        datum_type, datum_hex = _extract_datum_info(output)
        script_ref_lang = _extract_script_ref_info(output)

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
            datum_type=datum_type,
            datum_hex=datum_hex,
            script_ref_lang=script_ref_lang,
        )

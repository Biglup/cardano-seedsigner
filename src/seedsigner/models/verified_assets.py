"""Curated list of verified Cardano native assets.

Maps ``(policy_id, asset_name)`` to a display ticker, name, and decimal
count so token amounts can be rendered human-readably during review. An
asset is looked up per network: a policy ID is just a script hash, so the
same policy can exist on both mainnet and a testnet with unrelated tokens
behind it, a mainnet entry must never label a testnet asset (and vice
versa). Testnets share network id 0, so a testnet entry applies to preprod
and preview alike.

The list is hand-curated and reviewed entry by entry: each mainnet entry
was cross-checked against the Cardano Foundation token registry (which
carries the policy owner's signed metadata, including decimals) and an
independent market listing of the asset's policy ID. Inclusion bar:
market cap above $100k, or the token of an operating DeFi protocol (DEX,
lending, synthetics, oracle) whose circulating supply the market trackers
cannot verify. Anything not listed here falls back to the CIP-14
fingerprint display with raw amounts and an "Unknown decimals" warning.
Add new entries manually, verifying the policy ID against at least two
independent sources.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedAsset:
    """Display metadata for one curated native asset.

    decimals is the number of fractional digits the on-chain integer
    quantity carries, as attested by the token issuer.
    """
    ticker: str
    name: str
    decimals: int


MAINNET_ASSETS = {
    ("0691b2fecca1ac4f53cb6dfb00b7013e561d1f34403b957cbb5af1fa",
     "4e49474854"): VerifiedAsset("NIGHT", "NIGHT", 6),
    ("e824c0011176f0926ad51f492bcc63ac6a03a589653520839dc7e3d9",
     "464554"): VerifiedAsset("FET", "Artificial Superintelligence Alliance Token", 8),
    ("e5a42a1a1d3d1da71b0449663c32798725888d2eb0843c4dabeca05a",
     "576f726c644d6f62696c65546f6b656e58"): VerifiedAsset("WMTX", "World Mobile Token X", 6),
    ("279c909f348e533da5808898f87f9a14bb2c3dfbbacccd631d927a3f",
     "534e454b"): VerifiedAsset("SNEK", "Snek", 0),
    ("04b95368393c821f180deee8229fbd941baaf9bd748ebcdbf7adbb14",
     "7273455247"): VerifiedAsset("rsERG", "rsERG", 9),
    ("f43a62fdc3965df486de8a0d32fe800963589c41b38946602a0dc535",
     "41474958"): VerifiedAsset("AGIX", "SingularityNet AGIX Token", 8),
    ("c48cbb3d5e57ed56e276bc45f99ab39abe94e6cd7ac39fb402da47ad",
     "0014df105553444d"): VerifiedAsset("USDM", "USDM", 6),
    ("f66d78b4a3cb3d37afa0ec36461e51ecbde00f26c8f0a68f94b69880",
     "69555344"): VerifiedAsset("iUSD", "iUSD", 6),
    ("5d16cc1a177b5d9ba9cfa9793b07e60f1fb70fea1f8aef064415d114",
     "494147"): VerifiedAsset("IAG", "IAGON", 6),
    ("f13ac4d66b3ee19a6aa0f2a22298737bd907cc95121662fc971b5275",
     "535452494b45"): VerifiedAsset("STRIKE", "STRIKE", 6),
    ("a0028f350aaabe0545fdcb56b039bfb08e4bb4d8c4d7c3c7d481c235",
     "484f534b59"): VerifiedAsset("HOSKY", "HOSKY Token", 0),
    ("fe7c786ab321f41c654ef6c1af7b3250a613c24e4213e0425a7ae456",
     "55534441"): VerifiedAsset("USDA", "USDA", 6),
    ("29d222ce763455e3d7a09a665ce554f00ac89d2e99a1a83d267170c6",
     "4d494e"): VerifiedAsset("MIN", "Minswap", 6),
    ("8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61",
     "446a65644d6963726f555344"): VerifiedAsset("DJED", "Djed USD", 6),
    ("da8c30857834c6ae7203935b89278c532b3995245295456f993e1d24",
     "4c51"): VerifiedAsset("LQ", "Liqwid DAO Token", 6),
    ("5b26e685cc5c9ad630bde3e3cd48c694436671f3d25df53777ca60ef",
     "4e564c"): VerifiedAsset("NVL", "NuvolaDigital", 6),
    ("51a5e236c4de3af2b8020442e2a26f454fda3b04cb621c1294a0ef34",
     "424f4f4b"): VerifiedAsset("STUFF", "STUFF", 6),
    ("533bb94a8850ee3ccbe483106489399112b74c905342cb1792a797a0",
     "494e4459"): VerifiedAsset("INDY", "Indigo DAO Token", 6),
    ("2c5c6ca6f993e198bc9ac859ffb624dd291ec50b4d361544bd01e3ac",
     "584e4b"): VerifiedAsset("XNK", "Kinka Gold", 6),
    ("31bdb2d8ed6e2623e121b6db134a1491f4252b9ea87d928eb5290026",
     "496e66696e69747920526973696e67"): VerifiedAsset("RISE", "Infinity Rising Token", 6),
    ("edfd7a1d77bcb8b884c474bdc92a16002d1fb720e454fa6e99344479",
     "4e5458"): VerifiedAsset("NTX", "NuNet Utility Token", 6),
    ("b7c5cd554f3e83c8aa0900a0c9053284a5348244d23d0406c28eaf4d",
     "50414c4d0a"): VerifiedAsset("PALM", "PALM Economy Token", 6),
    ("eb7a93ebc321647673490810f618b548d7c24aa64d30ae342dba7076",
     "0014df10415343454e44"): VerifiedAsset("ASCEND", "Ascend", 6),
    ("49e423161ef818adc475c783571cb479d5f15ad52a01a240eacc0d3b",
     "434f434b"): VerifiedAsset("COCK", "COCK", 0),
    ("e992ef75f2367e6ecd93716ae88eba0d005dd91fd3a21f650b6496b5",
     "5355524745"): VerifiedAsset("SURGE", "SURGE", 6),
    ("8483844875ce4d61c2aa459240f277d32081ee08fe0ad16899a0f581",
     "0014df10544954414e"): VerifiedAsset("TITAN", "TITAN", 6),
    ("6d06570ddd778ec7c0cca09d381eca194e90c8cffa7582879735dbde",
     "584552"): VerifiedAsset("XER", "Xerberus DAO LLC", 6),
    ("c881c20e49dbaca3ff6cef365969354150983230c39520b917f5cf7c",
     "4e696b65"): VerifiedAsset("NIKEPIG", "NikePig", 0),
    ("7507734918533b3b896241b4704f3d4ce805256b01da6fcede430436",
     "42616279534e454b"): VerifiedAsset("BBSNEK", "BabySNEK", 0),
    ("c0ee29a85b13209423b10447d3c2e6a50641a15c57770e27cb9d5073",
     "57696e67526964657273"): VerifiedAsset("WRT", "WingRiders Governance Token", 6),
    ("94cbb4fcbcaa2975779f273b263eb3b5f24a9951e446d6dc4c135864",
     "52455655"): VerifiedAsset("REVU", "Revuto", 8),
    ("9ff9a1b456f074e03be90631e1a5f9b6ed08eacabd0e7f95a11ffff1",
     "0014df1041544c4153"): VerifiedAsset("ATLAS", "ATLAS", 6),
    ("5deab590a137066fef0e56f06ef1b830f21bc5d544661ba570bdd2ae",
     "424f44454741"): VerifiedAsset("BODEGA", "BODEGA", 6),
    ("ee8e065fe8d4f77d1f454709a535f284e902365ac0a1ff08ad19f9e8",
     "66474c44"): VerifiedAsset("fGLD", "fGLD", 0),
    ("8cfd6893f5f6c1cc954cec1a0a1460841b74da6e7803820dde62bb78",
     "524a56"): VerifiedAsset("RJV", "Rejuve Token", 6),
    ("97bbb7db0baef89caefce61b8107ac74c7a7340166b39d906f174bec",
     "54616c6f73"): VerifiedAsset("AGENT", "Agent", 0),
    ("fc11a9ef431f81b837736be5f53e4da29b9469c983d07f321262ce61",
     "4652454e"): VerifiedAsset("FREN", "FREN", 0),
    ("97075bf380e65f3c63fb733267adbb7d42eec574428a754d2abca55b",
     "436861726c6573207468652043686164"): VerifiedAsset("CHAD", "Charles the Chad", 0),
    ("8e51398904a5d3fc129fbf4f1589701de23c7824d5c90fdb9490e15a",
     "434841524c4933"): VerifiedAsset("C3", "CHARLI3", 6),
    ("a3931691f5c4e65d01c429e473d0dd24c51afdb6daf88e632a6c1e51",
     "6f7263666178746f6b656e"): VerifiedAsset("FACT", "Orcfax Token", 6),
    ("cc8d1b026353022abbfcc2e1e71159f9e308d9c6e905ac1db24c7fb6",
     "50617269627573"): VerifiedAsset("PBX", "Paribus", 6),
    ("9a9693a9a37912a5097918f97918d15240c92ab729a0b7c4aa144d77",
     "53554e444145"): VerifiedAsset("SUNDAE", "SUNDAE", 6),
    ("8fef2d34078659493ce161a6c7fba4b56afefa8535296a5743f69587",
     "41414441"): VerifiedAsset("LENFI", "Lenfi DAO token", 6),
    ("dda5fdb1002f7389b33e036b6afee82a8189becb6cba852e8b79b4fb",
     "0014df1047454e53"): VerifiedAsset("GENS", "Genius Yield Token", 6),
    ("95a427e384527065f2f8946f5e86320d0117839a5e98ea2c0b55fb00",
     "48554e54"): VerifiedAsset("HUNT", "HUNT", 6),
    ("c863ceaa796d5429b526c336ab45016abd636859f331758e67204e5c",
     "4353574150"): VerifiedAsset("CSWAP", "CSWAP", 6),
    ("afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb",
     "4d494c4b7632"): VerifiedAsset("MILK", "MILK", 6),
    ("804f5544c1962a40546827cab750a88404dc7108c0f588b72964754f",
     "56594649"): VerifiedAsset("VYFI", "VYFI", 6),
    ("8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61",
     "5368656e4d6963726f555344"): VerifiedAsset("SHEN", "Shen USD", 6),
    ("f66d78b4a3cb3d37afa0ec36461e51ecbde00f26c8f0a68f94b69880",
     "69425443"): VerifiedAsset("iBTC", "iBTC", 6),
    ("f66d78b4a3cb3d37afa0ec36461e51ecbde00f26c8f0a68f94b69880",
     "69455448"): VerifiedAsset("iETH", "iETH", 6),
    ("577f0b1342f8f8f4aed3388b80a8535812950c7a892495c0ecdf0f1e",
     "0014df10464c4454"): VerifiedAsset("FLDT", "FLDT", 6),
    ("f6099832f9563e4cf59602b3351c3c5a8a7dda2d44575ef69b82cf8d",
     ""): VerifiedAsset("OADA", "OADA", 6),
    ("2852268cf6e2db42e20f2fd3125f541e5d6c5a3d70b4dda17c2daa82",
     ""): VerifiedAsset("O", "The O Token", 6),
}

TESTNET_ASSETS = {}

NETWORK_ID__MAINNET = 1


def get_verified_asset(network, policy_id, asset_name):
    """The curated VerifiedAsset for a native token, or None when unlisted.

    network is a cometa NetworkId (or its integer value); policy_id and
    asset_name are cometa objects exposing ``to_bytes()``, as yielded by a
    transaction output's multi-asset map.
    """
    table = (MAINNET_ASSETS if int(network) == NETWORK_ID__MAINNET
             else TESTNET_ASSETS)
    return table.get((policy_id.to_bytes().hex(), asset_name.to_bytes().hex()))


def format_asset_amount(quantity: int, decimals: int) -> str:
    """Format an on-chain integer quantity using the asset's decimals.

    Exact integer arithmetic; trailing fractional zeros are dropped, like
    ``format_ada``.
    """
    sign = "-" if quantity < 0 else ""
    whole, fraction = divmod(abs(quantity), 10 ** decimals)
    formatted = f"{whole:,}"
    if decimals:
        frac_str = f"{fraction:0{decimals}d}".rstrip("0")
        if frac_str:
            formatted = f"{formatted}.{frac_str}"
    return f"{sign}{formatted}"

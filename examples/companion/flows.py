"""High-level companion flows shared by the example scripts."""

import uuid

from . import _paths  # noqa: F401

from cometa import NetworkId

from seedsigner.models.cardano_account import CardanoAccountRequest

from . import messages
from .wallet import WatchOnlyWallet


def request_account(device, account_index: int = 0,
                    network: NetworkId = NetworkId.TESTNET,
                    origin: str = "Companion") -> tuple:
    """STEP 1 — ask the device to export an account xpub + master fingerprint,
    and build a watch-only wallet from it.

    Returns ``(wallet, CardanoAccountResponse, request_cbor)``.
    """
    request = CardanoAccountRequest(
        request_id=str(uuid.uuid4()),
        account_indices=[account_index],
        origin=origin,
    )
    request_cbor = request.to_cbor()
    response_cbor = device.exchange(messages.UR_ACCOUNT_REQ, request_cbor, messages.UR_ACCOUNT_RES)
    response = messages.parse_response(messages.UR_ACCOUNT_RES, response_cbor)

    if response.request_id != request.request_id:
        raise ValueError("account response request_id does not match the request")

    key = next(k for k in response.keys if k.account_index == account_index)
    wallet = WatchOnlyWallet(
        account_xpub=key.xpub,
        master_fingerprint=response.master_fingerprint,
        account_index=account_index,
        network=network,
    )
    return wallet, response, request_cbor


def new_request_id() -> str:
    return str(uuid.uuid4())

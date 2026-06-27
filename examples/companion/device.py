"""The 'other device' the companion talks to.

Two implementations with the same ``exchange(req_type, req_cbor, res_type)`` API:

* ``SimulatedDevice`` — runs the real on-device codecs + signing core in-process
  from a known mnemonic. No QR, no hardware. Lets the whole e2e run (and CI test)
  offline, and is the reference for what the real device does.
* ``HardwareDevice`` — displays the request as an animated QR for the real
  SeedSigner's camera and scans the device's animated QR response back.
"""

from . import _paths  # noqa: F401

from . import messages


class SimulatedDevice:
    """In-process stand-in that runs the actual device signing core."""

    def __init__(self, mnemonic, passphrase: str = ""):
        from seedsigner.models.seed import Seed

        words = mnemonic.split() if isinstance(mnemonic, str) else list(mnemonic)
        self.seed = Seed(mnemonic=words, passphrase=passphrase)

    def exchange(self, req_type: str, req_cbor: bytes, res_type: str) -> bytes:
        if messages.RESPONSE_FOR_REQUEST.get(req_type) != res_type:
            raise ValueError(f"{req_type} does not produce {res_type}")

        if req_type == messages.UR_ACCOUNT_REQ:
            from seedsigner.models.cardano_account import build_account_response
            request = messages.parse_request(req_type, req_cbor)
            response = build_account_response(
                self.seed, request.request_id,
                request.account_indices, request.key_purpose)
            return response.to_cbor()

        if req_type == messages.UR_TX_SIG_REQ:
            from seedsigner.helpers.cardano_signing import build_tx_sign_response
            request = messages.parse_request(req_type, req_cbor)
            return build_tx_sign_response(self.seed, request).to_cbor()

        if req_type == messages.UR_CIP8_SIG_REQ:
            from seedsigner.helpers.cardano_signing import build_cip8_sign_response
            request = messages.parse_request(req_type, req_cbor)
            return build_cip8_sign_response(self.seed, request).to_cbor()

        raise ValueError(f"simulated device cannot handle {req_type}")


class HardwareDevice:
    """Talks to a real SeedSigner over animated QR in a single Tkinter window:
    the request QR is shown while the webcam watches for the device's response."""

    def __init__(self, max_fragment_len: int = 90, fps: float = 6.0,
                 camera: int = 0, width: int = 1280, height: int = 720, focus: int = None):
        from . import transport
        self._transport = transport
        self.max_fragment_len = max_fragment_len
        self.fps = fps
        self.camera = camera
        self.width = width
        self.height = height
        self.focus = focus

    def exchange(self, req_type: str, req_cbor: bytes, res_type: str) -> bytes:
        encoder = messages.make_encoder(req_type, req_cbor, self.max_fragment_len)
        return self._transport.exchange_qr(
            encoder, res_type,
            camera=self.camera, width=self.width, height=self.height,
            focus=self.focus, fps=self.fps,
        )

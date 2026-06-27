"""Make the in-repo ``seedsigner`` package importable from the companion.

The companion reuses the device's own UR transport (``seedsigner.helpers.ur2``)
and CBOR codecs (``seedsigner.models.cardano_account`` / ``cardano_tx``) so the
host and device can never drift on the wire format. Only the lightweight,
hardware-free modules are imported — never the GUI/display layer.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "..", "src"))

if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

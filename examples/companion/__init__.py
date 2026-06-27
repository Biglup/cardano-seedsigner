"""Host-side companion for the Cardano SeedSigner air-gapped signing demo.

Watch-only: it only ever holds account *public* keys (learned from the device's
account export), derives addresses, builds transactions, and verifies results.
It never sees private key material — the device signs.
"""

> Ported from the upstream [SeedSigner](https://github.com/SeedSigner/seedsigner) project (MIT, Copyright (c) 2021 SeedSigner), adapted for the Cardano QR protocol.

# QR Formats

### Scanning QR Codes

Cardano SeedSigner supports scanning the following QR formats:

Animated QR Formats (UR2, see the [protocol specification](cardano_seedsigner_air_gapped_hardware_wallet_specification_v1.1.pdf)):
- `cardano-tx-sig-req` — transaction signing request
- `cardano-cip8-sig-req` — CIP-8 message signing request
- `cardano-account-req` — account public key export request
- `settings` — settings import

Static QR Formats:
- Seed
    - [SeedSigner SeedQR](seed_qr/README.md) format
        - A 48 or 96 length string of numbers representing a BIP-39 wordlist. The numeric sequence is a concatenation of four-digit, zero-padded segments. Each four-digit segment represents a BIP-39 word expressed by a zero-indexed position in the wordlist. For example, "0000" is "abandon" in the English BIP-39 wordlist.
    - [SeedSigner CompactSeedQR](seed_qr/README.md) format
        - The 128- or 256-bit entropy encoded as a binary QR

### Displaying QR Codes

Cardano SeedSigner supports displaying QR codes in the following formats:

Animated QR Formats (UR2):
- `cardano-tx-sig-res` — vkey witness set for a signed transaction
- `cardano-cip8-sig-res` — COSE_Sign1 + COSE_Key for a signed message
- `cardano-account` — account public key export
- `settings` — settings export

Static QR Formats:
- Seed
    - SeedSigner SeedQR / CompactSeedQR backups (see above)

# Integration Guide

This one is for wallet and dApp developers who want to talk to a Cardano SeedSigner. The authoritative wire format lives in the [protocol specification](cardano_seedsigner_air_gapped_hardware_wallet_specification_v1.1.pdf) (chapter "QR Communication & UR Encoding Model", every payload has its CDDL there), this guide is the practical walkthrough: what to send, what you get back, and the mistakes that will get your request rejected.

There is also a full reference implementation in the repo under [`examples/`](../examples/), watch-only companion code that reuses the exact same codecs the device runs. If something here is ambiguous, the companion is the tiebreaker.

## Transport

Everything is UR2 (Blockchain Commons Uniform Resources) over animated QR. You encode your CBOR payload with the UR type string as discriminator (`cardano-tx-sig-req`, etc.), fragment it with fountain codes, and render the frames in a loop; the device scans until it recovers the payload, and answers the same way in the opposite direction. Payload bodies are plain untagged CBOR maps, the type string is the only discriminator, the registry ids you see in the spec (88000-88006) are reserved numbers that never appear on the wire. A fragment size around 90 bytes at ~6 fps scans reliably on typical webcams, the companion's `transport.py` has working numbers for both directions.

A single-part UR looks like:

```
ur:cardano-account-req/oxadksdkeoidehieihideeiedpecidemiedpeeidehihdpesiyeohsdpeyiaetiheehsesieehiydydyaoiyfejyihjpjtjzaxlyaeaacfatfnbtuedrdi
```

The body is minimal bytewords (2 chars per byte) over the CBOR plus a 4-byte CRC32 tail. When the payload doesnt fit one frame, the encoder emits numbered fountain frames instead:

```
ur:cardano-tx-sig-req/1-3/lpadaxcstocytieespwyhdfeosadksdkesieeohsenen...
ur:cardano-tx-sig-req/2-3/lpaoaxcstocytieespwyhdfepkpkpkpkpkpkpkpkpkpk...
```

`1-3` reads seqnum-seqlen. The receiver doesnt need frames in order and doesnt need all of them, keep cycling until the decoder reports completion (in practice ~1.75x the unique count when frames are being missed). seqnum keeps incrementing past seqlen as the encoder emits redundant combinations, that is normal, just keep displaying.

## Flow 1: account discovery

Send a `cardano-account-req` naming the accounts you want, the user approves on-device, you get back a `cardano-account` response with the 4-byte `master_fingerprint` and one CIP-1852 account xpub (64 bytes: pubkey || chaincode) per account.

Two things to get right:

- **Store the master fingerprint.** It is the identity of the seed and you must echo it back as the `xfp` field in every signing request later. A device with several seeds loaded uses it to route your request; a request whose xfp names no loaded seed cannot be signed.
- **Only ask for account 0** unless the user explicitly opted into multi-account on the device, requests naming other accounts get refused with the default settings.

From the account xpub you derive payment/stake/DRep keys with soft derivation (`role/index`, no hardened steps below the account level). `examples/companion/wallet.py` shows the derivation, address construction for base/enterprise/reward addresses, and the DRep ID encoding.

## Flow 2: transaction signing

You build and balance the transaction yourself (the device does not build transactions, it only signs), then send a `cardano-tx-sig-req` with:

- `sign_data`: the raw Conway-era transaction body CBOR, exactly what will be hashed and signed. Not the full transaction, just the body.
- `inputs`: one entry per UTxO being spent, each with `tx_hash`, `index`, and for key-locked inputs the owning `xfp` + derivation path. Script-locked inputs (multisig/Plutus) carry no path, their key witnesses go in `extra_signers`.
- `change_outputs`: the outputs that are your users own change, each with the output index and the derivation path that produces that address. The device re-derives and only badges the output as "Own / Verified Address" when it matches exactly. Base addresses are verified against the standard stake key (role 2 index 0), a base address with an exotic stake part will show as foreign.
- `extra_signers`: additional keys that must witness (minting policies, required signers), as (xfp, path) pairs.
- `network`: 0 testnet, 1 mainnet. If the body itself declares a network id it must agree, a mismatch is rejected before review.
- `collateral_return_path` (optional): same idea as change verification but for the collateral return output of a Plutus transaction.

Note the request carries **no resolved inputs / UTxO amounts**. The device cannot verify amounts you claim about the chain, so it does not display them as fact, the user reviews outputs and fee instead. Dont bother sending input values, there is no field for them, this is deliberate.

The response (`cardano-tx-sig-res`) is a standard vkey witness set: one Ed25519 signature over the Blake2b-256 body hash per distinct required key. Merge it into your full transaction (body + witness set + auxiliary data) and submit. `examples/sign_tx_e2e.py` runs this whole loop against Blockfrost preprod, from UTxO selection to broadcast.

### What gets a request rejected

- xfp not exactly 4 bytes, or an input path without its xfp
- tx_hash not 32 bytes
- derivation paths empty or longer than 10 components, or components over 32 bits (hardened = value + 0x80000000)
- body that doesnt parse as a Conway-era transaction body
- body network id contradicting the request network
- xfp naming a seed that isnt loaded (the user gets told which fingerprint the request wants)

## Flow 3: CIP-8 message signing

Send a `cardano-cip8-sig-req` with the payload bytes, the seed's `xfp`, the `required_signing_path`, and `address_bytes`, the credential the signature will be bound to: a full payment or stake address, or the bare 28-byte key hash for DRep signing.

The binding is enforced: the device derives the key at your path and refuses to sign when it does not control `address_bytes`. So derive the address from the same account xpub you got in flow 1 and you will always be consistent.

The response carries a `COSE_Sign1` and a `COSE_Key`. The wire format is the Ledger/Keystone one, protected header is the 2-field map `{1: -8, "address": <credential>}` with NO kid, unprotected is `{"hashed": false}`, and the COSE_Key kid equals the credential. This verifies in Lace and follows what CIP-95 dApps expect. If you need to verify signatures host-side, `examples/companion/cip8_verify.py` is a complete standalone verifier (rebuilds the Sig_structure and checks the Ed25519 signature and the key/credential binding).

## The packets on the wire, a full session

Formal CDDL for every payload is in the spec (chapter "QR Communication & UR Encoding Model", section "Payload Definitions"), what follows is one complete session shown packet by packet. Everything here is real output from the codecs, generated with the standard test mnemonic (`abandon` x11 + `about`, no passphrase), so you can reproduce every byte with the companion and diff against your own implementation. Amounts in diagnostic notation are plain CBOR, hardened path components are `value + 0x80000000` (so `2147485500` is `1852'`).

### 1. Host asks for account 0

```
a401782433623164656234642d356237642d346231652d396633612d3263386534613964
316630300266457465726e6c0381000419073c
```

```
{
  1: "3b1deb4d-5b7d-4b1e-9f3a-2c8e4a9d1f00",   ; request_id
  2: "Eternl",                                  ; origin
  3: [0],                                       ; account_indices
  4: 1852                                       ; key_purpose
}
```

### 2. Device answers with the account xpub

```
{
  1: "3b1deb4d-5b7d-4b1e-9f3a-2c8e4a9d1f00",   ; request_id echoed
  2: h'73c5da0a',                               ; master_fingerprint
  3: [
    {
      1: 0,                                     ; account index
      2: h'beb7e770b3d0f1932b0a2f3a63285bf9     ; 64-byte account xpub
           ef7d3e461d55446d6a3911d8f0ee55c0     ; (32 pubkey || 32 chaincode)
           b0e2df16538508046649d0e6d5b32969
           555a23f2f1ebf2db2819359b0d88bd16',
      3: [2147485500, 2147485463, 2147483648]   ; m/1852'/1815'/0'
    }
  ],
  4: "Cardano SeedSigner"                       ; device_label
}
```

`73c5da0a` is the value you now put in every `xfp` field for this seed. If you derive it yourself (BIP-32 master fingerprint over secp256k1) and it doesnt match, you are hashing the wrong thing, see the spec's "Fingerprints / Key Identification".

### 3. Host sends a transaction to sign

The body here is a minimal mainnet payment: one input, one output of 3 ADA, fee. `sign_data` is the body bytes verbatim, the device parses them itself:

```
body: a30081825820aaaa...aaaa01018182581d61111111111111111111111111111111
      111111111111111111111a002dc6c0021a0002a8b1
```

```
{
  1: "9d3a66e2-14fa-45c2-8b12-6e6f1d0aa001",
  2: "Eternl",
  3: h'a30081825820aa...a8b1',                  ; the 84-byte body above
  4: [                                          ; inputs
    {
      1: h'aaaa...aaaa',                        ; tx_hash (32 bytes)
      2: 1,                                     ; output index
      3: h'73c5da0a',                           ; xfp from step 2
      4: [2147485500, 2147485463, 2147483648, 0, 0]  ; m/1852'/1815'/0'/0/0
    }
  ],
  5: [],                                        ; change_outputs (none here)
  6: [],                                        ; extra_signers
  7: 1                                          ; network: mainnet
}
```

### 4. Device returns the witness set

```
{
  1: "9d3a66e2-14fa-45c2-8b12-6e6f1d0aa001",
  2: h'd90102818258207ea09a34aebb13c9841c71397b1cabfec5ddf950405293dee496
       cac2f437480a5840eedca1bd1f8ab43641554b5e2037e88fee6a68dc8af9733cba
       910977310366905de908e82dd1d712f3a5a94afb83e9f3012e70e1f49c482a71cf
       e8e863855304'
}
```

Key 2 decodes as a standard witness set: tag 258 (set) wrapping `[[vkey, signature]]`, the 32-byte public key at `m/1852'/1815'/0'/0/0` and the 64-byte Ed25519 signature over the body's Blake2b-256 hash (`fe109302cf698d4009a3931fe0207e659070d0ff493321522f4b1bf8ac22cf47` for this body). Verify it exactly like `verify_witnesses()` does in `examples/review_badges_demo.py`, then merge into your transaction as witness-set key 0 and submit.

### 5. CIP-8 message signing

Request, signing `"hello cardano"` with the payment key, bound to the base address of the same account:

```
{
  1: "5c07a1f4-9be2-4f8a-9d31-c4b2b19e8802",
  2: "Eternl",
  3: h'68656c6c6f2063617264616e6f',             ; "hello cardano"
  4: h'73c5da0a',                               ; xfp
  5: {1: 0, 2: [2147485500, 2147485463, 2147483648, 0, 0]},
  6: h'010fdc780023d8be7c9ff3a6bdc0d8d3b263bd0c ; base address (57 bytes,
       c12448c40948efbf42e557890352095f1cf6fd2b ; header 01 = base/mainnet)
       7d1a28e3c3cb029f48cf34ff890a28d176'
}
```

Response:

```
{
  1: "5c07a1f4-9be2-4f8a-9d31-c4b2b19e8802",
  2: h'8458...ea01',                            ; COSE_Sign1 (162 bytes)
  3: h'a501...480a'                             ; COSE_Key  (102 bytes)
}
```

The COSE_Sign1 unpacked:

```
[
  h'a2012767616464726573735839010fdc...d176',   ; protected (70 bytes), decodes to
                                                ;   {1: -8, "address": h'010fdc...d176'}
  {"hashed": false},                            ; unprotected
  h'68656c6c6f2063617264616e6f',                ; payload
  h'ddafd805ac8b157886ecaef07ef2d96bce5fa4f6    ; Ed25519 signature over
    2dcfb6f78c54621fcaa67c1845796514e02c7af3    ; the Sig_structure
    2cb6a8a5b1b64661c0bc3d64c6ac949b9ea1e49c
    b4b4ea01'
]
```

And the COSE_Key:

```
{
  1: 1,                                         ; kty: OKP
  2: h'010fdc...d176',                          ; kid = the bound address
  3: -8,                                        ; alg: EdDSA
  -1: 6,                                        ; crv: Ed25519
  -2: h'7ea09a34aebb13c9841c71397b1cabfe        ; the signing public key
       c5ddf950405293dee496cac2f437480a'
}
```

Note the protected header has exactly two fields and no `kid`, and the signature is over the COSE `Sig_structure` (`["Signature1", protected, h'', payload]`), not over the raw payload. If your verifier checks the raw payload it will fail, `examples/companion/cip8_verify.py` shows the correct reconstruction. For DRep signing key 6 carries the bare 28-byte key hash instead of a full address and the same value flows into `"address"` and `kid`.

## Testing without hardware

The companion ships a `SimulatedDevice` that runs the actual device signing core in-process, no GUI, no camera:

```bash
python examples/sign_message_e2e.py --simulator
python examples/review_badges_demo.py --simulator
python -m pytest examples/test_companion.py
```

Point your integration at `companion/device.py`'s `exchange()` API and you can CI the whole protocol offline, then swap `SimulatedDevice` for `HardwareDevice` (webcam + screen QR) and nothing else changes. This is how we test our own flows, is much faster than pointing cameras at screens all day.

## Getting a token on the verified list

The device ships a hand-curated list of well known native assets (`src/seedsigner/models/verified_assets.py`) that get ticker + decimals + a Verified badge in the review screens. Inclusion bar is market cap above $100k or being the token of an operating DeFi protocol, and every entry needs the policy id confirmed by at least two independent sources (CF token registry + a market listing). If your token qualifies, open a PR adding the entry, the well-formedness tests will catch most mistakes but reviewers will check the policy id against the sources themselves.

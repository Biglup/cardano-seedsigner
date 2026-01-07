# Cardano SeedSigner

Use an air-gapped Raspberry Pi Zero to sign for Cardano transactions

# Project Summary

The goal of Cardano SeedSigner is to reduce the cost and operational complexity of using Cardano wallets. To achieve this, SeedSigner enables users to build a verifiably air-gapped, stateless Cardano signing device using inexpensive, widely available hardware components—typically costing less than $50.

Cardano SeedSigner supports trustless private key generation and secure transaction authorization by relying exclusively on an offline execution model and a QR-based data exchange mechanism. This design eliminates network connectivity and persistent secret storage, allowing users to sign Cardano transactions and messages without exposing private key material to online systems.

Additional information about the SeedSigner project is available at https://seedsigner.com

Cardano SeedSigner is a forked and derivative work based on the original SeedSigner project developed by the SeedSigner contributors and available at
https://github.com/SeedSigner/seedsigner

# Attribution and License Notice

This project builds upon the [SeedSigner](https://github.com/SeedSigner/seedsigner) codebase, architecture, and design principles, extending them to support the Cardano blockchain while preserving the original project’s air-gapped security model and hardware abstractions.

The original SeedSigner project is licensed under the MIT License, and this project complies fully with the terms of that license. All applicable copyright notices, license text, and attribution are retained in accordance with MIT licensing requirements. No endorsement by the original SeedSigner authors is implied.

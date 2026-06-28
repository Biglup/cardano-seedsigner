class QRType:
    """
        Used with DecodeQR and EncodeQR to communicate qr encoding type
    """
    SEED__SEEDQR = "seed__seedqr"
    SEED__COMPACTSEEDQR = "seed__compactseedqr"
    SEED__UR2 = "seed__ur2"
    SEED__MNEMONIC = "seed__mnemonic"
    SEED__FOUR_LETTER_MNEMONIC = "seed__four_letter_mnemonic"

    SETTINGS = "settings"

    CARDANO_ACCOUNT_REQUEST = "cardano-account-req"
    CARDANO_ACCOUNT = "cardano-account"

    CARDANO_TX_SIG_REQUEST = "cardano-tx-sig-req"
    CARDANO_TX_SIG_RESPONSE = "cardano-tx-sig-res"
    CARDANO_CIP8_SIG_REQUEST = "cardano-cip8-sig-req"
    CARDANO_CIP8_SIG_RESPONSE = "cardano-cip8-sig-res"

    INVALID = "invalid"
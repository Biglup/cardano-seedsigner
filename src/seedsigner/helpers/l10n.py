import builtins


def mark_for_translation(message: str) -> str:
    # Wraps the target string literal for translation but does NOT return the translated string.
    return message


def gettext(message: str) -> str:
    """
    Translate a message using the currently installed translation.

    This function uses builtins._ which is installed by Settings.load_locale().
    Use this instead of `from gettext import gettext as _` to ensure locale
    changes take effect.
    """
    if hasattr(builtins, '_'):
        return builtins._(message)
    return message
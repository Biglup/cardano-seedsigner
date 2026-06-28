"""Step banners and status output for the demo scripts, so a recorded run reads
clearly at every stage (Export Extended Account Key, Build Transaction, Sign
Transaction, ...)."""

_WIDTH = 66


def step(number, total, title):
    """A prominent banner announcing the current stage."""
    bar = "=" * _WIDTH
    print(f"\n{bar}")
    print(f"  STEP {number}/{total}  {title}")
    print(bar)


def info(message):
    print(f"    {message}")


def action(message):
    """A QR scan / device interaction the operator needs to perform."""
    print(f"  >> {message}")


def ok(message):
    print(f"    [OK] {message}")


def result(label, value):
    print(f"    {label:<22}: {value}")

import pytest
from seedsigner.models.seed import InvalidSeedException, Seed


def test_seed_12_words():
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())

	assert seed.seed_bytes == b'q\xb3\xd1i\x0c\x9b\x9b\xdf\xa7\xd9\xd97H\xa8,\xa7\xd9>\xeck\xc2\xf5ND?, \x88-\x07\x9aa\xc5\xee\xb7\xbf\xc4x\xd6\x07 X\xb6}?M\xaa\x05\xa6\xa7(>\xbf\x03\xb0\x9d\xef\xed":\xdf\x88w7'

	assert seed.mnemonic_str == "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash"

	assert seed.passphrase == ""


def test_seed_15_words():
	"""15-word mnemonics (used by Daedalus) should be valid."""
	seed = Seed(mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon address".split())
	assert len(seed.mnemonic_list) == 15
	assert seed.seed_bytes is not None


def test_seed_24_words():
	"""24-word mnemonics should be valid."""
	seed = Seed(mnemonic="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art".split())
	assert len(seed.mnemonic_list) == 24
	assert seed.seed_bytes is not None


def test_seed_invalid_word_count():
	"""Word counts other than 12, 15, 24 should raise InvalidSeedException."""
	with pytest.raises(InvalidSeedException):
		Seed(mnemonic=["abandon"] * 11)

	with pytest.raises(InvalidSeedException):
		Seed(mnemonic=["abandon"] * 18)

	with pytest.raises(InvalidSeedException):
		Seed(mnemonic=["abandon"] * 21)


def test_fingerprint_deterministic():
	"""Same mnemonic should always produce the same fingerprint."""
	seed1 = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	seed2 = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	assert seed1.get_fingerprint() == seed2.get_fingerprint()


def test_fingerprint_changes_with_passphrase():
	"""Passphrase should change the fingerprint."""
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	fp_without = seed.get_fingerprint()
	seed.set_passphrase("test")
	fp_with = seed.get_fingerprint()
	assert fp_without != fp_with

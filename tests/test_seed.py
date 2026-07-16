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


def test_cardano_root_key_is_cached():
	"""Repeated access should return the same derived root key object."""
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	assert seed._cardano_root_key is None
	key = seed.cardano_root_key
	assert key is not None
	assert seed.cardano_root_key is key


def test_cardano_root_key_invalidated_by_passphrase():
	"""Setting a passphrase should drop the cache and change the derived key."""
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	key_without = seed.cardano_root_key
	seed.set_passphrase("test")
	assert seed._cardano_root_key is None
	key_with = seed.cardano_root_key
	assert key_with.get_public_key().to_bytes() != key_without.get_public_key().to_bytes()
	seed.set_passphrase("")
	assert seed.cardano_root_key.get_public_key().to_bytes() == key_without.get_public_key().to_bytes()


def test_root_key_from_seed_uses_cache():
	"""The shared helper should serve the Seed's cached root key."""
	from seedsigner.helpers.cardano_utils import root_key_from_seed
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	assert root_key_from_seed(seed) is seed.cardano_root_key


def test_set_passphrase_always_invalidates_cardano_root_key():
	"""The cache should be dropped even with regenerate_seed=False."""
	seed = Seed(mnemonic="obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split())
	seed.cardano_root_key
	seed.set_passphrase("test", regenerate_seed=False)
	assert seed._cardano_root_key is None


def test_finalize_pending_seed_warms_cardano_root_key():
	"""Finalizing a pending seed should eagerly derive the correct Cardano root key."""
	from seedsigner.models.seed_storage import SeedStorage
	storage = SeedStorage()
	mnemonic = "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split()
	seed = Seed(mnemonic=mnemonic)
	storage.set_pending_seed(seed)
	assert seed._cardano_root_key is None
	storage.finalize_pending_seed()
	assert seed._cardano_root_key is not None
	fresh_key = Seed(mnemonic=mnemonic).cardano_root_key
	assert seed._cardano_root_key.get_public_key().to_bytes() == fresh_key.get_public_key().to_bytes()


def test_finalize_duplicate_pending_seed_keeps_existing():
	"""Re-finalizing an equal seed should return the stored seed's index."""
	from seedsigner.models.seed_storage import SeedStorage
	storage = SeedStorage()
	mnemonic = "obscure bone gas open exotic abuse virus bunker shuffle nasty ship dash".split()
	storage.set_pending_seed(Seed(mnemonic=mnemonic))
	assert storage.finalize_pending_seed() == 0
	storage.set_pending_seed(Seed(mnemonic=mnemonic))
	assert storage.finalize_pending_seed() == 0
	assert storage.num_seeds() == 1

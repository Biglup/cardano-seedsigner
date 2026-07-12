# Releasing

## Versioning

The version is declared once, in `src/seedsigner/__init__.py`:

```python
__version__ = "0.1.0"
```

Everything else derives from it: the device shows it on the screensaver
(`Controller.VERSION`), and the packaging metadata reads it through setuptools
(`[tool.setuptools.dynamic] version = {attr = "seedsigner.__version__"}`).
`tests/test_version.py` fails if a second hardcoded version is reintroduced.

## Cutting a release

1. Bump `__version__` in `src/seedsigner/__init__.py` and commit it to `main`.
2. Tag the commit with a matching `v` prefix and push the tag:

   ```
   git tag v0.1.0
   git push origin v0.1.0
   ```

The tag push triggers `.github/workflows/release.yml`, which:

1. Verifies the tag equals `__version__` (a mismatch fails the run).
2. Builds the Raspberry Pi images (`pi0`, `pi2`, `pi02w`, `pi4`) against the
   `cardano-seedsigner-os` ref pinned in `release.yml` (`os-ref`).
3. Writes `SHA256SUMS`, GPG-signs each `.img` (detached `.img.asc`) and the
   checksums file (`SHA256SUMS.asc`).
4. Publishes a GitHub Release with the images, signatures, checksums, and the
   public key. A tag containing a hyphen (for example `v0.1.0-rc1`) is marked as
   a pre-release.

A tag whose version already contains a hyphen builds a pre-release; use a plain
`vMAJOR.MINOR.PATCH` tag for a final release.

## Image filenames and the OS ref

The image version comes from `git describe --tags` on both this repository and
`cardano-seedsigner-os`. When both carry the same tag the filename is
`cardano_seedsigner_os.<version>.<target>.img`; when they differ it combines
them as `cardano_seedsigner_os.os<os-version>_sw<app-version>.<target>.img`.

`os-ref` in `.github/workflows/release.yml` is pinned to a known OS tag so a
release always builds against a fixed image base. To produce a clean single
version filename, tag `cardano-seedsigner-os` with the same version and bump
`os-ref` to it before releasing (or set `os-ref: ${{ github.ref_name }}` to
release both repositories in lockstep, which requires the matching OS tag to
exist).

## Signing key

The private key lives only as an encrypted GitHub Actions secret; it is never
committed. The public key is committed so anyone can verify a release.

The secrets are scoped to a protected `release` environment rather than the
whole repository. Only the `release` job declares `environment: release`, so no
other workflow (for example `build.yml`, which runs on every push to `main`)
can read them, and a required reviewer must approve the run before the key is
exposed. This means a merged change or a pushed tag cannot exfiltrate the key
without a human approving the release.

One-time maintainer setup:

1. Generate a signing key (Ed25519 or RSA 4096):

   ```
   gpg --full-generate-key
   ```

2. Create the environment: Settings -> Environments -> New environment, named
   `release`. Under its protection rules, add yourself (and any co-maintainers)
   as a required reviewer.

3. Add the private key and passphrase as secrets of the `release` environment
   (not repository secrets): `GPG_SIGNING_KEY` and `GPG_PASSPHRASE`. Export the
   armored private key with:

   ```
   gpg --armor --export-secret-keys <KEY_ID>
   ```

   Paste the full armored block as the `GPG_SIGNING_KEY` value.

4. Export the public key and commit it to the repository root as
   `cardano_seedsigner_pubkey.gpg`:

   ```
   gpg --export <KEY_ID> > cardano_seedsigner_pubkey.gpg
   ```

Also restrict who can push tags and create releases (Settings -> branch and tag
protection), so only trusted maintainers can trigger the release run at all.

If `GPG_SIGNING_KEY` is not set, the release still builds and publishes but is
left unsigned and the run emits a warning. The runner imports the key into a
throwaway keyring under the runner temp directory, passes the passphrase through
a file that never touches the command line, keeps all key material out of the
build workspace and release assets, and destroys the keyring when the job ends.

## Verifying a release

```
gpg --import cardano_seedsigner_pubkey.gpg
gpg --verify SHA256SUMS.asc SHA256SUMS
sha256sum -c SHA256SUMS
```

Each image can also be verified directly against its detached signature, using
whatever the release asset is named:

```
gpg --verify <image>.img.asc <image>.img
```

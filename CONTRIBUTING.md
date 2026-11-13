# Contributing to VORTHYX

Bug reports, focused fixes, documentation, and experimental forks are welcome.

For a recovery bug, include the VORTHYX commit, host OS and architecture, Python and Nuitka versions when known, the exact command, and the relevant redacted report. Prefer a small source fixture you wrote and can share over uploading an application binary. Explain the expected behavior and the observed result.

Never attach credentials, private conversations, commercial source trees, or software you cannot redistribute. Do not put private recovered code into a public issue. Follow [SECURITY.md](SECURITY.md) for security-sensitive findings.

## Development

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q validation
python nuitka_decompiler.py --help
python nuitka_decompiler.py --ndx --help
```

The engine currently lives in one large module. Keep patches narrow, explain the compiler pattern or invariant they address, and avoid sample-name or address-specific shortcuts. For recovery changes, add a synthetic regression that demonstrates the failure and the intended semantics. A syntax-only assertion is not enough to establish equivalent behavior.

The optional compiled fixture matrix requires Nuitka and a native compiler; see [validation/README.md](validation/README.md). The ordinary test suite does not certify arbitrary binaries or every protection mode.

Preserve copyright and license notices. Link related issues and describe validation in your pull request. Contributions are made under this repository's MIT license.

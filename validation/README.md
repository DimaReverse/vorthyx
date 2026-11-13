# Validation

Run the existing regression suite from the repository root:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q validation
```

The tests cover source-audit diagnostics, selected renderer behavior, synthetic metadata cases, and the comparison harness. A PE-fixture integration test is skipped unless `NDX_STATIC_PE_FIXTURE` points to a suitable local file; that binary is not distributed.

## Optional compiled fixture matrix

With Nuitka and an appropriate native compiler installed:

```sh
python validation/run_matrix.py --output .perf/matrix_current
```

Choose a new or empty output directory. The runner compiles four controlled fixtures, recovers each extension statically, and compares selected original and recovered functions using deterministic local stubs. The fixture functions and recovered counterparts are executed during comparison. The compiled target applications are not launched.

The runner records environment details, hashes, logs, and individual results. It can invoke Nuitka's toolchain download flow. Inspect the script before running it in an offline environment. Use a separate output directory for each interpreter/compiler configuration.

The initial publication checks did not run this compiled matrix. Existing fixtures may expose known recovery gaps; a passing case is not a compatibility claim for an entire platform or Nuitka release. See [limitations](../docs/LIMITATIONS.md).

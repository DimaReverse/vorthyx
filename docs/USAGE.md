# Usage

Run commands from the repository root, in an activated virtual environment. All examples use files you own or are authorized to inspect.

## NDX interface

The `--ndx` switch selects a separate argument parser. Always include it for the commands in this section; the legacy parser has different options and defaults.

```sh
python nuitka_decompiler.py --ndx --help
python nuitka_decompiler.py --ndx ./your_app.exe -o ./recovered --dev-only
python nuitka_decompiler.py --ndx ./your_app.exe -o ./recovered --only 'mypackage.*,__main__'
python nuitka_decompiler.py --ndx ./your_app.exe -o ./recovered --strict
```

`--dev-only` uses module classification to omit libraries; inspect the results if a wanted module is missing. `--only` accepts comma-separated globs. Quote them to prevent your shell from expanding `*`.

ABI discovery without source recovery:

```sh
python nuitka_decompiler.py --ndx ./your_app.exe -o ./abi-report --abi-only
```

Export surviving embedded bytecode separately:

```sh
python nuitka_decompiler.py --ndx ./your_app.exe -o ./bytecode --export-bytecode
```

Use `--target-python 3.11` only when you know the target's runtime version and automatic metadata discovery is unavailable. It describes the target, not the interpreter launching VORTHYX. `--abi-only` and `--export-bytecode` cannot be combined.

## Results and exit status

NDX source recovery writes Python source and `HEXPYRION_REPORT.json`; ABI discovery writes `ABI_REPORT.json`, and bytecode export writes `BYTECODE_MANIFEST.json` alongside its artifacts. Some legacy names remain for compatibility.

Inspect report fields such as `source_recovery`, partial modules, failed modules, and unresolved bodies. Output names and available artifacts depend on the path taken and the input.

For the NDX source-recovery command:

| Status | Meaning |
| --- | --- |
| `0` | The command completed under its selected policy; equivalence is unproven. |
| `1` | Recovery failed. |
| `2` | Invalid CLI input, or detectable gaps with `--strict`. Inspect stderr and reports to distinguish these. |
| `130` | Interrupted by the user. |

Keep outputs separate from the repository and use a fresh output directory when comparing versions.

## Legacy interface

These commands use the parser selected when `--ndx` and `--dev-only` are absent:

```sh
python nuitka_decompiler.py --help
python nuitka_decompiler.py --source ./your_app.exe --list-modules
python nuitka_decompiler.py --source ./your_app.exe --onefile-unpack -o ./unpacked
```

The legacy interface also contains extraction, reconstruction, and explicit runtime instrumentation paths. Its `--live-decompile` name refers to a recovery interface; do not infer execution behavior from a flag name alone. Runtime trigger/injection paths are distinct from static recovery and may launch or interact with a target process. This guide focuses on static analysis.

## Optional dependencies

| Dependency | Purpose |
| --- | --- |
| `requirements.txt` | Capstone native disassembly, pefile PE parsing, Zstandard decompression. |
| `requirements-bytecode.txt` | xdis metadata for optional cross-version bytecode handling. |
| `requirements-native-recovery.txt` | Unicorn for bounded callback-backed metadata recovery. Not needed for all inputs. |
| External bytecode decompilers | Optional conversion of surviving `.pyc` artifacts; separate from native source reconstruction. Compatibility varies by Python version. |

The legacy bytecode fallback includes a path that attempts to install decompiler packages with pip. Use an isolated virtual environment, and avoid that path when you need an offline, dependency-stable analysis. `--no-pyc-decompile` skips the legacy automatic `.pyc` decompilation phase. The NDX native-recovery quick start does not require an external bytecode decompiler.

## Troubleshooting

- **Missing Capstone:** install requirements with the same `python` used to run the command.
- **Python DLL conflicts on Windows:** launch from a clean directory outside a target's extracted runtime; do not add its `.pyd` files to your environment.
- **Missing or partial source:** inspect diagnostics before changing budgets. Unknown metadata grammars and optimized compiler patterns can remain unsupported.
- **Wrong CLI options:** check whether you selected NDX or legacy mode, then read that interface's `--help`.
- **Unexpected runtime behavior in recovered code:** keep the original and recovered versions isolated and compare a controlled fixture. Parsing and an exit status of zero do not prove identical semantics.

Set `NO_COLOR=1` in your environment for plain output. Terminal colors are disabled when output is redirected.

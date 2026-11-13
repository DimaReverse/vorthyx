# Publication review

This review concerns the supplied `nuitka_decompiler_suprim.py`, published here as `nuitka_decompiler.py`. The engine was copied byte for byte; this packaging release changes documentation and the test import filename, not its recovery algorithms.

## Structure

The supplied file has 158,727 lines and 3,583 function definitions including nested functions. It combines a legacy pipeline with an integrated NDX engine. The final entry point selects NDX when `--ndx` or `--dev-only` is present; otherwise it calls the legacy parser.

NDX components include `BinaryImage`, ABI discovery, constants/module metadata recovery, helper classification, `BodyLifter2`, `Structurer`, `NdxRenderer`, and `ModuleEmitter`. The legacy section includes extraction, static disassembly, reconstruction, optional external bytecode tooling, and explicit runtime instrumentation components.

## Findings relevant to users

- Native recovery and embedded bytecode export must be documented separately; neither proves that every original Python module is recoverable.
- Broad container parsing is not the same as full native-lifter support across architectures and compiler versions.
- The legacy bytecode fallback can invoke pip to install packages. The usage guide calls this out; the NDX quick start does not require that path.
- Runtime trigger/instrumentation paths execute or interact with a target process. They must not inherit a blanket claim that every mode is static or that target code can never run.
- NDX parses a positional `output_pos`, but the subsequent recovery call uses `args.output`. Use explicit `-o` in documented commands. This potential CLI defect is preserved for a separate focused fix.
- The legacy top-level broad exception handler prints a fatal error without explicitly returning a nonzero status. Do not use its exit status alone to judge recovery success.
- Overlapping components and repeated definitions in a single module make maintenance and review difficult. Modularization should preserve the final authoritative definitions and CLI behavior.

## Checks performed

- Parsed the source with Python's AST parser and compiled it without launching a target binary.
- Exercised both `--help` paths.
- Ran the included existing regression suite: 35 passed, one optional external-fixture test skipped.
- Verified that the copied engine matches the original bytes before Git's newline normalization.
- Checked common GitHub-token, AWS-access-key, private-key-header, and Telegram-token patterns; no matches found. This is a limited pattern scan, not a guarantee that no sensitive data exists anywhere in the source.
- Checked relative Markdown links and restricted the publication folder to selected source, synthetic fixtures, documentation, and repository configuration.

No target application was launched. No end-to-end compiled fixture matrix, performance comparison, exhaustive semantic audit, or exhaustive security audit was performed for this publication. See [limitations](LIMITATIONS.md).

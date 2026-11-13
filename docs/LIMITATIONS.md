# Recovery limits

VORTHYX is a research preview. Optimizing compilation can discard names, structure, and distinctions present in the original Python source. Recovery cannot recreate evidence that is no longer available with certainty.

## Coverage is specific to each stage

Container readers have PE, ELF, and Mach-O paths. That does not imply complete native source recovery for every container, CPU architecture, Nuitka release, compiler, or optimization profile. Native analysis concentrates on x86-64 patterns; other architecture-related code is not a support guarantee.

Embedded bytecode, if present, is a different artifact from Nuitka-compiled native code. Exporting it does not establish that every module has been recovered. Python bytecode and marshal formats depend on the target interpreter version.

Some callback-backed registries can be analyzed with the optional bounded emulator. Finding a native entry point does not establish that the associated constants grammar or source body is recoverable. Custom or protected metadata can remain unresolved. Themida/WinLicense removal is not supplied by this repository.

## Reports have limits too

`--strict` detects certain reported gaps. It cannot detect every semantic error. A syntactically valid function, a complete-looking report, or a passing fixture does not prove equivalence for arbitrary inputs.

Legacy recovery includes tentative and heuristic paths, including opt-in options that affect how incomplete bodies are emitted. Preserve provenance and uncertainty annotations when evaluating results. Never treat reconstructed output as trusted code merely because it can be imported.

## Publication checks

The initial package was checked locally on Windows with Python 3.11. The included regression suite produced **35 passed and 1 skipped**. The skipped test requires an optional external PE fixture (`NDX_STATIC_PE_FIXTURE`), which is intentionally not distributed.

These are synthetic regression and comparison-harness checks. The compiled Nuitka fixture matrix was not run for this publication. Earlier workspace reports and third-party application samples are not bundled or used to claim compatibility or performance here. No head-to-head comparison with HEXPYRION or REVENANT was performed.

The current engine is a large single module. Its overlapping legacy and NDX components make review and maintenance harder; modularization is future work, not a completed feature. This publication review is not an exhaustive correctness or security audit of every code path.

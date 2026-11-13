# Publishing this prepared repository

The package is prepared for **DimaReverse/vorthyx** as a new public repository. Existing repositories are not overwritten. The initial publication environment could not reach the GitHub API from its shell; local preparation is separate from a verified GitHub publication.

From a PowerShell session with Git, GitHub CLI, and working network access:

```powershell
gh auth login -h github.com
cd C:\path\to\vorthyx
.\scripts\Publish-GitHub.ps1
```

Skip login if `gh api user --jq .login` already returns `DimaReverse`. Never paste access tokens into issues or conversations.

The script checks the authenticated account and clean working tree, creates the public repository if no origin is configured, pushes `main` and `v0.1.0`, sets the description, homepage, issues and topics, and creates a preview release using the prepared notes. It does not force-push or replace an existing project. A name collision stops creation for review.

Topics: `nuitka`, `decompiler`, `reverse-engineering`, `static-analysis`, `python`, `source-recovery`, `unpacker`, `bytecode`, `binary-analysis`, `research`.

After publication, inspect the actual GitHub Actions result before claiming Windows/Linux or Python 3.12 validation. The workflow is configured, but a local test pass is not a hosted CI result.

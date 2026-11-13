# Run from PowerShell on a machine with GitHub CLI access.
# Creates the public DimaReverse/vorthyx repository and preview release.
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$repoName = 'DimaReverse/vorthyx'

function Invoke-Gh {
    param([string[]]$Arguments)
    & gh @Arguments
    if ($LASTEXITCODE -ne 0) { throw "GitHub command failed: gh $($Arguments -join ' ')" }
}

Push-Location -LiteralPath $repoRoot
try {
    $account = & gh api user --jq .login
    if ($LASTEXITCODE -ne 0) { throw 'GitHub is unreachable or authentication failed. Check connectivity and run gh auth login if needed.' }
    if ($account.Trim() -ne 'DimaReverse') { throw "Expected DimaReverse; authenticated as $account. No repository was created." }

    $changes = & git status --porcelain
    if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Commit or resolve local changes before publication.' }
    & git rev-parse --verify 'refs/tags/v0.1.0' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Expected local v0.1.0 tag is missing.' }

    $remoteNames = @(& git remote)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect Git remotes.' }
    if ('origin' -notin $remoteNames) {
        # Creation fails safely if that repository name is already taken.
        Invoke-Gh -Arguments @('repo', 'create', $repoName, '--public', '--source', '.', '--remote', 'origin', '--push', '--description', 'Nuitka native code to readable Python: static source recovery, bytecode export and onefile extraction. By DimaReverse.')
    } else {
        $originUrl = & git remote get-url origin
        if ($LASTEXITCODE -ne 0) { throw 'Unable to read origin URL.' }
        if ($originUrl.Trim() -notin @('https://github.com/DimaReverse/vorthyx.git', 'https://github.com/DimaReverse/vorthyx', 'git@github.com:DimaReverse/vorthyx.git')) {
            throw "Unexpected origin: $originUrl. No push performed."
        }
        & git push -u origin main
        if ($LASTEXITCODE -ne 0) { throw 'Push failed.' }
    }

    Invoke-Gh -Arguments @('repo', 'edit', $repoName, '--homepage', 'https://dimareverse.netlify.app', '--enable-issues', '--add-topic', 'nuitka,decompiler,reverse-engineering,static-analysis,python,source-recovery,unpacker,bytecode,binary-analysis,research')
    & git push origin v0.1.0
    if ($LASTEXITCODE -ne 0) { throw 'Tag push failed.' }

    & gh release view v0.1.0 --repo $repoName *> $null
    if ($LASTEXITCODE -ne 0) {
        Invoke-Gh -Arguments @('release', 'create', 'v0.1.0', '--repo', $repoName, '--verify-tag', '--prerelease', '--title', 'VORTHYX 0.1.0 - Open research preview', '--notes-file', 'docs/RELEASE_NOTES.md')
    }
    Invoke-Gh -Arguments @('repo', 'view', $repoName, '--json', 'url,visibility,repositoryTopics')
    Write-Host 'Published: https://github.com/DimaReverse/vorthyx'
} finally {
    Pop-Location
}

# Distribution channels

## What works

| Channel | Cost | Status |
| --- | --- | --- |
| **GitHub Releases** | free | installers for Windows, macOS (Apple Silicon + Intel), Linux, attached automatically on a `v*` tag |
| **PyPI** (`pip install oqp-studio`) | free | wheel bundles the server, UI, viewer and sketcher; published on tag when `PYPI_API_TOKEN` is set |
| **conda-forge** | free | natural next step — OpenQP users already use conda |
| **Homebrew cask / Scoop** | free | optional one-command installs, pointing at the release assets |

Cutting a release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

That single tag builds every installer, attaches them plus the wheel to a
public GitHub release page that needs no login, and publishes to PyPI if the
token secret exists.

## What does not work, and why

**Google Play** distributes Android apps only. OQP Studio is a desktop
application built on Tauri (a native webview plus a Python backend that spawns
OpenQP), so there is nothing to submit. An Android build would mean a
different product: a thin client talking to a remote OpenQP server, since
phones cannot run the Fortran core.

**Mac App Store** requires the App Sandbox. The Studio's whole purpose is to
execute a separately installed `openqp` binary — from a conda environment,
`/usr/local/bin`, or WSL — and to read and write job directories the user
chooses. A sandboxed app may not launch executables outside its own bundle,
and Apple rejects apps that depend on separately installed command-line
tools. Passing review would mean removing the ability to run calculations.

**Microsoft Store** is possible: registration is now free, and unpackaged
`.exe`/`.msi` installers have been accepted since 2021. But submissions must
be Authenticode-signed by a certificate chaining to a Microsoft-trusted CA,
so the Store does not avoid the signing cost (see
[code-signing.md](code-signing.md)). It is worth doing only alongside a
Windows certificate.

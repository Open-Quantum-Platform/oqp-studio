# Desktop shell (Tauri 2)

Scaffolded Tauri 2 project wrapping the frontend, targeting native installers:

- Windows: MSI / NSIS
- macOS: DMG
- Linux: AppImage / deb

## Layout

```
src-tauri/
  Cargo.toml         Rust crate (tauri 2 + shell plugin)
  tauri.conf.json    window, dev server (:5173), frontend dist, bundling
  src/main.rs        app entry
  capabilities/      window permission set
  icons/             placeholder icons (replace with real OQP artwork,
                     plus icon.ico/icon.icns before Windows/macOS bundling)
```

## Developing

Requires Rust (stable) and the Tauri 2 Linux prerequisites
(webkit2gtk-4.1, libappindicator, etc. — see tauri.app docs):

```bash
cargo install tauri-cli --version "^2"
cd shell/src-tauri
cargo tauri dev      # starts the Vite dev server and opens the window
cargo tauri build    # bundles installers for the host OS
```

The scaffold compiles against the Vite dev server / built dist. Remaining
Phase 0 shell work, in order:

1. Sidecar: bundle the PyInstaller-frozen backend and spawn it on startup
   (tauri-plugin-shell), wait for `/api/health`, then navigate the window to
   the backend origin so UI + viewer + API share one origin.
2. Real icons (icon.ico, icon.icns) and file associations
   (`.oqp`, `.molden`, `.cube`, `.hess.json`).
3. GitHub Actions release workflow with tauri-action for 3-OS installers.

Note: this scaffold has not yet been compiled in CI (the Linux build needs
webkit2gtk system packages); it is committed as the starting point for the
first machine with the Tauri toolchain.

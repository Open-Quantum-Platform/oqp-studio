# Desktop shell (Tauri 2)

This directory will hold the Tauri 2 project that wraps the frontend and
manages the backend process, producing native installers:

- Windows: MSI / NSIS
- macOS: DMG (universal)
- Linux: AppImage / deb

## Planned setup

```bash
npm create tauri-app@latest   # points at ../frontend as the dev server
```

Shell responsibilities:

1. Spawn/stop the Python backend (PyInstaller-frozen `oqp-studio-backend`)
   as a sidecar process and wait for `/api/health`.
2. Serve the built frontend from `../frontend/dist`.
3. Native menus, file associations (`.oqp`, `.molden`, `.cube`, `.hess.json`),
   and auto-update.

The Tauri scaffold is intentionally not committed yet — it requires a Rust
toolchain and will be added on a machine with cargo available (tracked as
Phase 0 remaining work).

# Desktop shell (Tauri 2)

Tauri 2 shell wrapping the frontend and the frozen backend. It builds the
published installers: MSI/NSIS on Windows, DMG and `.app` tarball on macOS,
AppImage and `.deb` on Linux — each in a plain and a `-with-engine` variant.

## Layout

```
src-tauri/
  Cargo.toml         Rust crate (tauri 2 + shell plugin)
  tauri.conf.json    window, dev server (:5173), frontend dist, bundling
  src/main.rs        app entry
  capabilities/      window permission set
  binaries/          where the frozen backend is staged (empty in git)
  icons/             placeholder icons (replace with real OQP artwork)
```

## Developing

Requires Rust (stable) and, on Linux, the Tauri 2 prerequisites
(webkit2gtk-4.1, libappindicator — see the tauri.app docs).

```bash
cargo install tauri-cli --version "^2"
cd shell/src-tauri
cargo tauri dev      # starts the Vite dev server and opens the window
cargo tauri build    # bundles installers for the host OS
```

`cargo tauri dev` needs a frozen backend staged in `binaries/` first, because
`externalBin` declares one; the repository ships that directory empty. See
"Working on the desktop shell" in the top-level README for the one-time build,
and for why most work does not belong in this loop at all.

Note that `devUrl` matters less here than the name suggests. The window opens
on the Vite dev server, but `main.rs` navigates it to the backend origin as
soon as the backend answers, so what you end up looking at is served from
`frontend/dist` — one origin for UI, viewer and API, which is the layout the
shipped app relies on.

## What the shell does

1. Spawns the PyInstaller-frozen backend as a sidecar, passing
   `OQP_STUDIO_RESOURCES` so it can find an engine bundled by the installer —
   the resource directory sits next to the executable on Windows, in
   `Contents/Resources` on macOS, and under `/usr/lib` on Linux, and only
   Tauri knows which.
2. Skips that spawn when a backend of the *same version* already answers on
   the port; anything else, and it starts its own on a free one.
3. Shows a splash with a running counter while it waits, up to 180 seconds,
   then navigates to the backend origin.
4. Names `backend.log` on the failure screen, because the message alone gives
   nobody anything to act on.

## Remaining

- Real icons (`icon.ico`, `icon.icns`) and file associations for `.oqp`,
  `.molden`, `.cube`, `.hess.json`.
- Code signing and notarization; see [../docs/code-signing.md](../docs/code-signing.md).
- The sidecar's output receiver is dropped, so the backend's stderr goes
  nowhere. Forwarding it to `backend.log` would make startup observable in
  the field rather than only on a developer's machine.

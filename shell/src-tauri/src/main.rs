#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// OQP Studio desktop shell (Phase 0).
//
// The window loads the frontend (Vite dev server in `tauri dev`, the built
// dist in release). Remaining Phase 0 shell work: spawn the PyInstaller-frozen
// backend as a sidecar via tauri-plugin-shell, wait for /api/health, and point
// the window at the backend origin so the UI, viewer, and API share one origin.

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("error while running OQP Studio");
}

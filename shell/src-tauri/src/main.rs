#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// OQP Studio desktop shell.
//
// On startup: spawn the bundled backend binary (sidecar), wait until its TCP
// port accepts connections, then navigate the main window to the backend
// origin so UI, results viewer, and API all share http://127.0.0.1:<port>.

use std::net::TcpStream;
use std::time::Duration;

use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

struct Backend(std::sync::Mutex<Option<CommandChild>>);

fn backend_port() -> u16 {
    std::env::var("OQP_STUDIO_PORT")
        .ok()
        .and_then(|value| value.parse().ok())
        .unwrap_or(8814)
}

fn wait_for_port(port: u16, timeout: Duration) -> bool {
    let deadline = std::time::Instant::now() + timeout;
    while std::time::Instant::now() < deadline {
        if TcpStream::connect(("127.0.0.1", port)).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    false
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Backend(std::sync::Mutex::new(None)))
        .setup(|app| {
            let port = backend_port();

            // Reuse an already-running backend (e.g. a dev server); otherwise
            // spawn the bundled sidecar.
            if TcpStream::connect(("127.0.0.1", port)).is_err() {
                let (_rx, child) = app
                    .shell()
                    .sidecar("oqp-studio-backend")?
                    .args(["--port", &port.to_string()])
                    .spawn()?;
                *app.state::<Backend>().0.lock().unwrap() = Some(child);
            }

            let window = app
                .get_webview_window("main")
                .expect("main window missing");
            std::thread::spawn(move || {
                if wait_for_port(port, Duration::from_secs(30)) {
                    let url = format!("http://127.0.0.1:{port}")
                        .parse()
                        .expect("valid backend url");
                    let _ = window.navigate(url);
                } else {
                    let _ = window.eval(
                        "document.body.innerHTML = \
                         '<p style=\"font-family:sans-serif;padding:2rem\">\
                          OQP Studio backend failed to start.</p>'",
                    );
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building OQP Studio")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(child) = app.state::<Backend>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}

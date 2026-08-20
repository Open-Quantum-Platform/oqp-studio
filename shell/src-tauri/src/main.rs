#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

// OQP Studio desktop shell.
//
// On startup: spawn the bundled backend binary (sidecar), wait until its TCP
// port accepts connections, then navigate the main window to the backend
// origin so UI, results viewer, and API all share http://127.0.0.1:<port>.

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
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

/// The version reported by a backend already listening on `port`.
///
/// A previous release left running keeps port 8814 open, and simply reusing
/// whatever answers there would serve that old version's UI and API inside
/// the new app — which looks exactly like the upgrade never happened.
fn probe_version(port: u16) -> Option<String> {
    let address = format!("127.0.0.1:{port}").parse().ok()?;
    let mut stream = TcpStream::connect_timeout(&address, Duration::from_millis(700)).ok()?;
    stream.set_read_timeout(Some(Duration::from_millis(1500))).ok()?;
    stream
        .write_all(
            b"GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n",
        )
        .ok()?;
    let mut response = String::new();
    stream.read_to_string(&mut response).ok()?;
    let key = "\"version\":\"";
    let start = response.find(key)? + key.len();
    let rest = &response[start..];
    let end = rest.find('"')?;
    Some(rest[..end].to_string())
}

/// A port nothing is listening on, starting the search at `start`.
fn free_port(start: u16) -> u16 {
    (start..start.saturating_add(64))
        .find(|port| TcpListener::bind(("127.0.0.1", *port)).is_ok())
        .unwrap_or(start)
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
            let requested = backend_port();

            // Reuse a backend on the usual port only when it is this same
            // version — an older copy still running would otherwise serve its
            // own UI here. Anything else, and this app starts its own on a
            // port that is actually free.
            let matching = probe_version(requested).as_deref() == Some(env!("CARGO_PKG_VERSION"));
            let port = if matching { requested } else { free_port(requested) };
            if !matching {
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
                    // The version query makes the URL unique per release, so an
                    // upgraded app can never be served the previous version's
                    // cached page.
                    let url = format!(
                        "http://127.0.0.1:{port}/?v={}",
                        env!("CARGO_PKG_VERSION")
                    )
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

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

/// Shown until the backend answers. Written as a script rather than a page so
/// it works whatever the window happens to have loaded, and cleared by the
/// navigation that replaces it.
const SPLASH: &str = r#"(function () {
  var show = function () {
    document.body.innerHTML =
      '<div style="position:fixed;inset:0;display:flex;align-items:center;' +
      'justify-content:center;background:#15161a;color:#e6e7ea;' +
      'font-family:-apple-system,Segoe UI,sans-serif">' +
      '<div style="text-align:center;line-height:1.6">' +
      '<div style="font-size:1.1rem">Starting OQP Studio</div>' +
      '<div style="opacity:.6;font-size:.9rem;margin-top:.4rem">' +
      'unpacking the compute environment — <span id="oqp-splash-secs">0s</span>' +
      '</div></div></div>';
    var t0 = Date.now();
    setInterval(function () {
      var el = document.getElementById('oqp-splash-secs');
      if (el) { el.textContent = Math.round((Date.now() - t0) / 1000) + 's'; }
    }, 500);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', show);
  } else {
    show();
  }
})();"#;

/// Where the backend records a startup failure; kept in step with
/// server_main.log_path() on the Python side.
fn backend_log() -> std::path::PathBuf {
    let base = if cfg!(target_os = "macos") {
        dirs_home().join("Library/Application Support/OQP Studio")
    } else if cfg!(target_os = "windows") {
        std::env::var_os("APPDATA")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(dirs_home)
            .join("OQP Studio")
    } else {
        std::env::var_os("XDG_CONFIG_HOME")
            .map(std::path::PathBuf::from)
            .unwrap_or_else(|| dirs_home().join(".config"))
            .join("oqp-studio")
    };
    base.join("backend.log")
}

fn dirs_home() -> std::path::PathBuf {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(std::path::PathBuf::from)
        .unwrap_or_default()
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
                // Where an installer that carries the compute engine put it.
                // The backend cannot work this out reliably on its own: the
                // resource directory sits next to the executable on Windows,
                // in Contents/Resources on macOS, and under /usr/lib on Linux.
                // Tauri knows, so it says so.
                let mut env = std::collections::HashMap::new();
                if let Ok(resources) = app.path().resource_dir() {
                    env.insert(
                        "OQP_STUDIO_RESOURCES".to_string(),
                        resources.to_string_lossy().to_string(),
                    );
                }
                let (_rx, child) = app
                    .shell()
                    .sidecar("oqp-studio-backend")?
                    .args(["--port", &port.to_string()])
                    .envs(env)
                    .spawn()?;
                *app.state::<Backend>().0.lock().unwrap() = Some(child);
            }

            let window = app
                .get_webview_window("main")
                .expect("main window missing");

            // Say what is happening while it happens. The backend takes
            // fourteen to twenty seconds to open its port on a healthy
            // machine -- it unpacks an interpreter, NumPy, SciPy and RDKit
            // before it can answer anything -- and a window that is blank for
            // that long is a window that looks broken.
            let _ = window.eval(SPLASH);

            std::thread::spawn(move || {
                // Generously longer than the twenty seconds this takes when
                // it is working. The old thirty-second limit was close enough
                // to that to turn a slow disk into "failed to start".
                if wait_for_port(port, Duration::from_secs(180)) {
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
                    // Name the file the backend writes its traceback to: the
                    // message on its own gives the user, and us, nothing to
                    // act on.
                    let log = backend_log().to_string_lossy().to_string();
                    let _ = window.eval(&format!(
                        "document.body.innerHTML = \
                         '<div style=\"font-family:sans-serif;padding:2rem;line-height:1.5\">\
                          <p>OQP Studio backend failed to start.</p>\
                          <p style=\"opacity:.7\">Details are in<br><code>{log}</code></p>\
                          </div>'"
                    ));
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

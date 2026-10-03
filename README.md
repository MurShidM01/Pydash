# Pydash

**Live UI preview for Pydrud** — a native Android app written in Python with
[Pydrud](https://github.com/MurShidM01/Pydrud) 2.0.2.

Run `pydrud dev` on your computer, scan the QR code with Pydash, and your
project's UI renders *natively inside the app* over Wi-Fi — taps, scrolls,
text input and dialogs included — with no APK rebuilds. Pydash speaks the
same versioned, authenticated preview protocol the generated Android runtime
uses, then draws the mirrored widget tree with the real renderer, not a
re-implementation.

Pydash is a preview client and nothing else — think *Expo Go for Pydrud*.
It ships no widget catalog or demo playground of its own; every screen
exists to connect, show and manage a live preview session.

## What's inside

| Area | What it is |
| --- | --- |
| **Home** | Connection dashboard: status pill, server details, live sync statistics, reconnect/disconnect controls — and always one tap to scan the `pydrud dev` QR code. |
| **Live Preview** | The client side of `pydrud dev`: camera QR capture (ML Kit) or manual entry, a revisioned widget-tree mirror with a patch applier, and a native renderer for the remote project's UI. |
| **Settings** | Theme mode (system/light/dark), brand re-seeding, haptics, keep-awake, auto-reconnect, plus protocol versions and About info. |

## Using Pydash to preview your own project

1. Install the Pydrud CLI 2.0.2 and make sure your phone and computer share
   a network.
2. Build and install Pydash once (see *Developing Pydash* below), then
   launch it on your phone.
3. In **your** Pydrud project:

   ```bash
   pydrud dev      # serves your project and prints a QR + pydrud:// URI
   ```

4. In Pydash, tap **Scan** and point the camera at the QR code — or use any
   scanner app: the payload is a `pydrud://preview/connect?…` deep link that
   opens Pydash directly. No camera? Paste the URI (or type
   host/port/session/token) in manual entry.

The dev server listens on TCP **8597** by default. Sessions are authenticated
per-run with a bearer token, and the connection self-heals: if Wi-Fi drops,
Pydash retries with exponential backoff (0.6 s → 8 s, up to 12 attempts) and
re-synchronises the tree on reconnect — the mirror NACKs stale patches and
the server answers with a recovery snapshot.

While connected you get the full loop: your taps and scrolls travel back as
events, the project's `State` changes come down as incremental patches, and
hot reload of your Python code re-renders the preview instantly.

### How the preview protocol works

```
 Pydash (client)                     pydrud dev (server)
 ───────────────                     ───────────────────
 preview_hello  ────────────────►   (versions, session, token,
 ◄────────────  preview_welcome      capabilities, metrics)
 ready (metrics) ───────────────►
 ◄────────────  theme                pushed right after welcome
 ◄────────────  render_transaction   snapshot @ rev 1
 render_ack ────────────────────►
 click/change/scroll events ─────►
 ◄────────────  render_transaction   patches @ rev 2… (or snapshot)
 render_ack / render_nack ───────►   NACK ⇒ recovery snapshot
```

`ready` (with live device metrics) triggers one more render on the server so
the layout adapts to the real screen; after that, only actual changes go
over the wire.

The handshake (`pydrud.preview` v1) is versioned separately from the
renderer protocol (v2); both are checked before a single widget is sent, and
the server refuses unknown versions, wrong credentials or missing renderer
capabilities with a structured rejection code.

## Developing Pydash itself

```bash
pydrud dev              # host Python + LAN live-preview QR (meta: preview Pydash in Pydash)
pydrud run              # build, install, launch with Flutter-style Hot Reload (r/R)
python run.py           # headless: build the widget tree on your computer
python run.py --tree    #   dump the full tree as JSON
python run.py --tab     #   verify every tab body constructs
python -m pytest tests/ # run the test suite (54 tests)
```

`pydrud dev` and `pydrud run` are separate workflows: preview never builds
an APK, while `run` uses the generated Android app and embedded Python
runtime.

## Project layout

```
Pydash/
├── run.py                  dev runner (headless: tree build / JSON dump / tab check)
├── pydrud.yaml             SDK, NDK, package name, permissions, capabilities
├── pydrud.toml             Python packages bundled into the APK + theme seed
├── android/                the generated native layer — `pydrud sync` refreshes it
├── tests/                  app, mirror, URI-parser and end-to-end protocol tests
└── src/
    ├── pydrud_config.py    runtime configuration for the device
    └── app/
        ├── main.py         route table, deep links, App bootstrap
        ├── config.py       identity, versions, wire-protocol constants
        ├── state.py        the State objects every screen shares
        ├── theme.py        brand seed + Pydash design-token configuration
        ├── runtime.py      the router and the live App handle (`refresh()`)
        ├── jobs.py         background work (WorkManager)
        ├── ui.py           compatibility imports for older generated apps
        ├── preview/        the client side of `pydrud dev`
        │   ├── uri.py      parse & validate the QR payload
        │   ├── models.py   connection states, endpoint & server metadata
        │   ├── client.py   socket client: handshake, transactions, events
        │   ├── mirror.py   mirrored remote widget tree + patch applier
        │   ├── session.py  session state machine + auto-reconnect
        │   └── renderer.py renders the mirrored tree natively in Pydash
        ├── components/     reusable UI: layout, brand hero, status pill, states
        └── screens/        one module per screen
            ├── shell.py        tabbed root (Home · Settings)
            ├── home.py         the connection dashboard
            ├── scan.py         camera QR capture + manual entry
            ├── preview.py      the live-preview host screen
            └── settings.py     appearance, connection behaviour, About
```

### Routes

| Route | Screen | Notes |
| --- | --- | --- |
| `shell` | Tabbed root | initial route |
| `scan` | QR scanner + manual entry | pushed, `slide_up` |
| `preview` | Live preview host | `fade` |
| `/preview/connect` | Deep link from a `pydrud dev` QR | validates and connects immediately |

Deep links work with both the app's own `pydash://` scheme and the
`pydrud://preview/connect?…` URI printed by `pydrud dev` — both are declared
in the manifest, so any scanner app can hand a QR payload to Pydash.

## Add a screen

1. Create `src/app/screens/profile.py` with a `profile_screen(page, params)`
   function.
2. Register it in `src/app/main.py`:
   `router.define("profile", profile_screen)`.
3. Navigate from any handler with `router.push("profile")`, passing data as
   `router.push("profile", params={"id": 7})`.

All Pydash-owned widget keys use the `pd_` prefix so they can never collide
with the mirrored remote tree, whose keys arrive verbatim from the dev
server.

## Android configuration

`pydrud.yaml` is the source of truth for the generated Android project:
app/package identity, release version, SDK/NDK/toolchain versions, ABIs,
assets, permissions, capabilities and deep links. Edit it and run
`pydrud sync`. Keep Python packages and the theme seed in `pydrud.toml`; app
code under `src/app/` is never overwritten by sync.

The project declares the `CAMERA` permission (for QR scanning) plus the
`haptics` and `notifications` capabilities — camera access is requested at
runtime, only when you open the scanner. For your own features, prefer
Python-first commands such as `pydrud capabilities add haptics` and
`pydrud permissions add camera`; never hand-edit generated Android files.

## Useful commands

Pydrud commands share the Hot Reload runner's terminal UI: clear phases,
status badges, summaries and next-step hints.

| Command | What it does |
| --- | --- |
| `pydrud dev` | run Python locally and wait for an authenticated Pydash preview client |
| `pydrud sync` | apply `pydrud.yaml` and regenerate managed Android files |
| `pydrud analyze` | static checks on your Python UI code |
| `pydrud pip add requests` | bundle a Python package into the APK |
| `pydrud permissions add camera` | add a permission to the manifest |
| `pydrud capabilities add haptics` | enable generated feature bundles |
| `pydrud build --release` | signed release build |
| `pydrud doctor` | check your toolchain |

## Tests

The suite runs on plain Python (`python -m pytest tests/`) and needs no
device:

| File | What it covers |
| --- | --- |
| `test_app.py` | every screen, tab switching, connection flows and deep links via `pydrud.testing.AppTester` |
| `test_uri.py` | QR payload parsing and validation rules |
| `test_mirror.py` | the remote tree mirror and every patch op (`create`/`delete`/`move`/`replace`/`update`) |
| `test_preview_protocol.py` | end-to-end wire contract — handshake, rejection codes, revisioned transactions, ACK/NACK, resync, events and service bridge — against a real `pydrud.App` served by `tests/preview_server_harness.py` |

## License

[MIT](LICENSE)

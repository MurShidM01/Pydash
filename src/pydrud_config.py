"""Generated Pydrud configuration for the Pydash app.

Edit pydrud.yaml and run `pydrud sync` for Android projects.
"""

# ── App metadata ─────────────────────────────────────────────────────────────
APP_NAME = "Pydash"
PACKAGE = "com.pydrud.pydash"
VERSION = "1.0.2"
VERSION_CODE = 2
ASSETS_DIR = "assets"
PERMISSIONS = ["CAMERA"]
CAPABILITIES = ["haptics", "notifications"]

# ── Android SDK ──────────────────────────────────────────────────────────────
MIN_SDK = 24
TARGET_SDK = 36
COMPILE_SDK = 36

# ── Local Chaquopy bridge ────────────────────────────────────────────────────
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 8595

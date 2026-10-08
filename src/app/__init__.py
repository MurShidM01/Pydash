"""Pydash — the live-preview client for Pydrud.

An Expo-Go-style Android app: run ``pydrud dev`` on your computer, scan the QR
code (or paste the connection URL), and the project's UI renders natively
inside Pydash over Wi-Fi — no APK rebuilds.

Layout:

* ``config``   — identity, versions, wire-protocol and design constants
* ``theme``    — the palette, generated from one brand colour (+ ``theme.pss``)
* ``state``    — the shared :class:`~pydrud.State` objects
* ``runtime``  — the router and the running app (``refresh()`` lives here)
* ``preview``  — the client side of ``pydrud dev`` (protocol, mirror, session)
* ``components`` — reusable UI building blocks shared by screens
* ``screens``    — one module per screen
* ``main``       — route registration and the start-up entry point
"""

__version__ = "1.0.2"

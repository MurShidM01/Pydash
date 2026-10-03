"""Pydash — application package.

Pydash is the live-preview companion app for Pydrud: a developer runs
``pydrud dev`` on their machine, scans the QR code from Pydash, and the
project's UI renders natively inside Pydash with incremental updates —
no APK rebuilds.

Layout:

* ``config``     — identity, versions and wire-protocol constants
* ``state``      — the shared :class:`~pydrud.State` objects
* ``runtime``    — the router, the running app and UI-thread scheduling
* ``theme``      — the Pydash design system on top of Pydrud's Theme
* ``components`` — reusable UI building blocks shared by screens
* ``preview``    — the live-preview client (protocol, session, renderer)
* ``data``       — the component catalog and playground demo registry
* ``screens``    — one module per screen family
* ``jobs``       — background work run by WorkManager
* ``main``       — route registration and the start-up entry point
"""

__version__ = "1.0.0"

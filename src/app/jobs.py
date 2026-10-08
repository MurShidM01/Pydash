"""Background jobs.

WorkManager calls :func:`run_background_job` from ``PydrudWorker``, possibly
while the UI is gone, so these functions must never touch widgets. Register a
job with ``@job("name")`` and schedule it from a screen with
``page.background.schedule("name", every=900)``.

Pydash itself schedules no background work — the live preview is entirely
foreground — but the entry point is kept so a future "notify me when my dev
server comes online" job has a home.
"""

import json

JOBS = {}


def job(name):
    """Decorator registering a background job by name."""
    def decorator(fn):
        JOBS[name] = fn
        return fn
    return decorator


def run_background_job(name, inputs_json="{}"):
    """Entry point invoked by PydrudWorker.java."""
    from pydrud.core.tasks import GLOBAL_JOBS
    handler = JOBS.get(name) or GLOBAL_JOBS.get(name)
    if handler is None:
        return f"no such job: {name}"
    try:
        payload = json.loads(inputs_json or "{}")
    except ValueError:
        payload = {}
    return json.dumps(handler(payload), default=str)

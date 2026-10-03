"""Live widget demos, grouped by widget family.

Each module exposes one ``CATEGORY`` whose demos build real Pydrud widgets.
Every builder receives a key prefix and returns a widget tree; interactive
demos read/write module-level :class:`~pydrud.State` objects and call
:func:`app.runtime.refresh` from their handlers, exactly the way real app
code does.
"""

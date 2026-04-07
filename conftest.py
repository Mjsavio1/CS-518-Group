import warnings

# Enable NiceGUI's pytest plugin when optional UI test deps are installed.
try:
	import selenium  # noqa: F401
	from nicegui.testing import Screen  # noqa: F401

	pytest_plugins = ["nicegui.testing.plugin"]
except Exception:
	pytest_plugins = []
	warnings.warn(
		"NiceGUI pytest plugin disabled (optional dependency missing, e.g. selenium)."
	)
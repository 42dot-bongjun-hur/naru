from contextlib import contextmanager
from contextvars import ContextVar

from naru.config import BuildConfig

_active_config: ContextVar[BuildConfig] = ContextVar("naru_build_config")


@contextmanager
def use_config(config: BuildConfig):
	token = _active_config.set(config)
	try:
		yield
	finally:
		_active_config.reset(token)


def __getattr__(name: str):
	if not name.isupper():
		raise AttributeError(name)
	try:
		config = _active_config.get()
	except LookupError as error:
		raise RuntimeError("Naru build configuration is not active") from error
	paths = {
		"BASE_DIR": config.site_root,
		"OUT_DIR": config.output_dir,
		"DATA_DIR": config.site_root / "content" / "data",
		"POSTS_DIR": config.site_root / "content" / "posts",
		"TPL_DIR": config.site_root / "templates",
		"STATIC_DIR": config.site_root / "static",
	}
	if name in paths:
		return paths[name]
	try:
		return config.settings[name.lower()]
	except KeyError as error:
		raise AttributeError(name) from error

"""Build-scoped Jinja rendering with site overrides and escaped data."""

from contextlib import contextmanager
from contextvars import ContextVar

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    StrictUndefined,
)

from . import config as engine_config
from .routes import archive_path, content_path, site_root_path, tag_path

_active_templates: ContextVar[Environment] = ContextVar("naru_templates")


def default_template_names() -> list[str]:
    return PackageLoader("naru", "defaults/templates").list_templates()


def create_template_environment(settings: dict) -> Environment:
    environment = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(engine_config.TPL_DIR),
            PackageLoader("naru", "defaults/templates"),
        ]),
        autoescape=True,
        undefined=StrictUndefined,
    )
    environment.globals.update(
        site=settings,
        content_url=content_path,
        tag_url=tag_path,
        archive_url=archive_path,
        site_root_url=site_root_path,
        **{key.upper(): value for key, value in settings.items()},
    )
    return environment


@contextmanager
def use_templates(settings: dict):
    token = _active_templates.set(create_template_environment(settings))
    try:
        yield
    finally:
        _active_templates.reset(token)


def current_templates() -> Environment:
    return _active_templates.get()


def render_template(name: str, **context) -> str:
    return current_templates().get_template(name).render(**context)


class TemplateFragment:
    def __init__(self, environment, name, context):
        self.environment = environment
        self.name = name
        self.context = context

    def __html__(self):
        return self.environment.get_template(self.name).render(**self.context)

    def __bool__(self):
        return bool(self.__html__())
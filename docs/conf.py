"""Конфигурация Sphinx для документации tbank."""

from __future__ import annotations

project = "tbank"
author = "masasibata"
copyright = "2026, masasibata"

try:
    from tbank import __version__ as release
except ImportError:  # pragma: no cover
    release = "0.1.0"
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.autodoc_pydantic",
    "myst_parser",
]

# --- autodoc ---
autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# --- autodoc-pydantic: чистый рендер моделей ---
autodoc_pydantic_model_show_json = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_member_order = "bysource"
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_field_show_alias = True  # показывать wire-имя поля (PascalCase/camelCase)
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_field_show_constraints = False

# --- intersphinx ---
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# --- MyST ---
myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}

# superpowers/ — локальные рабочие доки, не для публикации.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "superpowers",
    "superpowers/**",
    "requirements.txt",
]

html_theme = "furo"
html_title = f"tbank {release}"
language = "ru"

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
    "myst_parser",
]

autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {"members": True, "show-inheritance": True}
napoleon_google_docstring = True
napoleon_numpy_docstring = False

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
html_title = "tbank"
language = "ru"

# Не падать, если необязательные зависимости для autodoc отсутствуют.
autodoc_mock_imports: list[str] = []

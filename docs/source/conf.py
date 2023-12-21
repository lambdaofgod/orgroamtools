# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os, sys

sys.path.insert(0, os.path.abspath("../../"))
# sys.path.insert(0, os.path.abspath("../.."))
# sys.path.insert(0, os.path.abspath("../"))
# sys.path.insert(0, os.path.abspath("."))
print(sys.path)

project = "orgroamtools"
copyright = "2023, abaxi"
author = "abaxi"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
autodoc_mock_imports = [
    "networkx",
    "re",
    "os",
    # "orgroamtools",
    "sqlite3",
    "copy",
    "typing",
    "dataclasses",
]
from unittest.mock import MagicMock

mock_modules = [
    "networkx",
    "enum",
    "dataclasses",
    "typing",
    "__future__",
    "os",
    "re",
    "warnings",
    "sqlite3",
    "copy",
]
for name in mock_modules:
    sys.modules[name] = MagicMock()

extensions = ["sphinx.ext.napoleon", "sphinx.ext.autodoc"]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

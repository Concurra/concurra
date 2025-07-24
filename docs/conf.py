# Configuration file for the Sphinx documentation builder.

import os
import sys
sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------

# -- Logo & Static Files --
html_logo = "concurra_logo.png"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_js_files = ["inject.js"]
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    "navigation_with_keys": True,
    'logo_only': True,
    'display_version': False
}

html_context = {
    "display_github": False,
    "github_user": "Concurra",
    "github_repo": "concurra",
    "github_version": "main",
    "conf_py_path": "/docs/",
    "display_version": False
}

project = "Concurra"
author = "Sahil Pardeshi"
release = "1.0.0"

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",  # Enables Markdown support
]

# Allow both .rst and .md source files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# The master toctree document.
master_doc = "index"


# -- MyST Parser options -----------------------------------------------------

myst_enable_extensions = [
    "deflist",
    "colon_fence",
    "tasklist",
    "fieldlist",
]

# -- Extra metadata for Read the Docs ----------------------------------------

# If you want to include a logo:
# html_logo = "_static/concurra_logo.png"

# Optional: set the language
language = "en"

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sphinx_rtd_theme

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../..'))
sys.setrecursionlimit(1500)


# -- Project information -----------------------------------------------------

project = 'Kube Docs'
copyright = '2020, Shaun Cullen'
author = 'Shaun Cullen'

# The full version, including alpha/beta/rc tags
release = '0.0.1'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx_rtd_theme',
    'sphinx.ext.autosectionlabel',
    'sphinxcontrib.mermaid',
]

default_role = 'code'

autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 4

mermaid_params = ['--theme', 'forest', '--width', '600', '--backgroundColor', 'transparent']

mermaid_cmd = "C:\\Users\\shaun\\Development\\kube_docs\\node_modules\\.bin\\mmdc.cmd"

mermaid_output_format = "png"

latex_documents = [('index',            # top-level file (index.rst)
                    f"kube_docs_{release.replace('.', '_')}",           # output (target.pdf)
                    'Kube Docs',   # document title
                    'Shaun Cullen',
                    "manual")]   # document author

html_theme_options = {
    'navigation_depth': 4,
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

latex_elements = {
    'papersize': 'letterpaper',
    'pointsize': '10pt',
    'preamble': '',
    'figure_align': 'htbp'
}
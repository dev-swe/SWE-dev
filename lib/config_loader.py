# -*- coding: utf-8 -*-
"""
config_loader.py
----------------
Single source of truth for loading config.py across the SWE-dev extension.

Works from any file in the extension tree:
  - lib/               (1 dirname up to EXTENSION_DIR)
  - a pushbutton/      (4 dirnames up to EXTENSION_DIR)

Usage (in any script):
    from config_loader import load_extension_config
    _CONFIG = load_extension_config(__file__)
    SP_FILE       = _CONFIG.get('SP_FILE')
    PROJECTS_ROOT = _CONFIG.get('PROJECTS_ROOT')
"""

import os
import io
import sys

try:
    from pyrevit import forms as _forms
    _HAS_FORMS = True
except ImportError:
    _HAS_FORMS = False


def _alert_exit(msg):
    if _HAS_FORMS:
        _forms.alert(msg, exitscript=True)
    else:
        raise RuntimeError(msg)


def load_extension_config(caller_file):
    """Locate config.py by walking up from *caller_file*, load it, and return
    the resulting namespace dict.  Adds lib/ to sys.path as a side-effect.

    Parameters
    ----------
    caller_file : str
        Pass ``__file__`` from the calling module.

    Returns
    -------
    dict
        The namespace produced by exec-ing config.py.
    """
    path = os.path.abspath(caller_file)
    for _ in range(8):
        path = os.path.dirname(path)
        cfg = os.path.join(path, 'config.py')
        if os.path.exists(cfg):
            lib_dir = os.path.join(path, 'lib')
            if lib_dir not in sys.path:
                sys.path.insert(0, lib_dir)
            ns = {}
            try:
                with io.open(cfg, 'r', encoding='utf-8') as f:
                    exec(f.read(), ns)
            except Exception as ex:
                _alert_exit(
                    "Could not read config.py:\n{0}".format(ex)
                )
            return ns
    _alert_exit(
        "Missing config.py (searched 8 levels up from {0})".format(caller_file)
    )
    return {}

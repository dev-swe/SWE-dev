# -*- coding: utf-8 -*-
"""
utils.py
--------
Light-weight utility helpers shared across all SWE-dev scripts.

No Revit API imports — safe to import at module level in any context.

Usage:
    from utils import current_username, current_timestamp, safe_filename
"""

import os
import datetime


def current_username():
    """Return the current OS username, or an empty string if not resolvable."""
    return (
        os.environ.get('USERNAME', '')
        or os.environ.get('USER', '')
        or ''
    )


def current_timestamp(timespec='seconds'):
    """Return the current local time as an ISO-8601 string.

    Parameters
    ----------
    timespec : str
        Passed directly to ``datetime.isoformat()``. Defaults to ``'seconds'``.
    """
    return datetime.datetime.now().isoformat(timespec=timespec)


def safe_filename(text):
    """Replace characters that are unsafe in file/folder names with underscores.

    Preserves alphanumeric characters, hyphens, and underscores.

    Parameters
    ----------
    text : str
        The raw string to sanitise.

    Returns
    -------
    str
        A filesystem-safe version of *text*.
    """
    return ''.join(
        c if (c.isalnum() or c in ('-', '_')) else '_'
        for c in (text or '')
    )

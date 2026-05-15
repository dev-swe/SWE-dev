# -*- coding: utf-8 -*-
"""
project_paths.py
----------------
Revit project path resolution for the SWE-dev extension.

Resolves the SWE Project Number from Revit ProjectInformation,
builds the project root folder path, finds the CAD subfolder,
and returns canonical paths for dashboard and sync-queue JSON files.

Usage:
    from project_paths import get_dashboard_json_path, get_sync_queue_json_path
"""

import os
import glob

from pyrevit import forms
from config_loader import load_extension_config
from utils import safe_filename

# ==================== CONFIG ====================

_CONFIG       = load_extension_config(__file__)
PROJECTS_ROOT = _CONFIG.get('PROJECTS_ROOT')

if not PROJECTS_ROOT:
    forms.alert(
        "PROJECTS_ROOT is missing in config.py",
        exitscript=True
    )


# ==================== PROJECT NUMBER ====================

def get_swe_project_number(doc):
    """Return the SWE Project Number string from Revit ProjectInformation,
    or ``None`` if not set."""
    if not doc:
        return None
    try:
        project_info = doc.ProjectInformation
        for param in project_info.Parameters:
            try:
                if param.Definition and param.Definition.Name == 'SWE Project Number':
                    value = param.AsString()
                    if value:
                        value = value.strip()
                        if value:
                            return value
            except Exception:
                pass
    except Exception:
        pass
    return None


# ==================== FOLDER RESOLUTION ====================

def get_project_root(doc):
    """Return the top-level project folder path, or ``None``."""
    project_number = get_swe_project_number(doc)
    if not project_number:
        return None
    return os.path.join(PROJECTS_ROOT, project_number)


def get_cad_folder(doc):
    """Return the first "10 CAD*" subfolder inside the project root, or ``None``."""
    project_root = get_project_root(doc)
    if not project_root or not os.path.exists(project_root):
        return None
    matches = [
        p for p in glob.glob(os.path.join(project_root, '10 CAD*'))
        if os.path.isdir(p)
    ]
    if not matches:
        return None
    matches.sort()
    return matches[0]


def pick_folder():
    """Prompt the user to choose a folder; returns the path or ``None``."""
    folder = forms.pick_folder()
    if folder and os.path.isdir(folder):
        return folder
    return None


def get_storage_folder(doc, prompt_user=True):
    """Return the best available storage folder for this project.

    Falls back to a manual picker if no CAD folder is resolved and
    ``prompt_user`` is ``True``.
    """
    cad_folder = get_cad_folder(doc)
    if cad_folder:
        return cad_folder
    if not prompt_user:
        return None
    forms.alert(
        'No SWE Project Number or 10 CAD folder was found.\n'
        'Please select a folder for the dashboard files.',
        warn_icon=False
    )
    return pick_folder()


# ==================== JSON PATH HELPERS ====================

def get_project_json_path(doc, filename, prompt_user=True):
    """Return ``<storage_folder>/<filename>``, or ``None``."""
    folder = get_storage_folder(doc, prompt_user=prompt_user)
    if not folder:
        return None
    return os.path.join(folder, filename)


def get_dashboard_json_path(doc, prompt_user=True):
    """Return the canonical path for the coordination dashboard JSON file."""
    title = doc.Title if doc else 'Project'
    return get_project_json_path(
        doc,
        safe_filename(title) + '_coordination_dashboard.json',
        prompt_user=prompt_user,
    )


def get_sync_queue_json_path(doc, prompt_user=True):
    """Return the canonical path for the sync-queue JSON file."""
    return get_project_json_path(doc, 'sync_queue.json', prompt_user=prompt_user)

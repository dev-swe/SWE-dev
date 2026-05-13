# -*- coding: utf-8 -*-
import os
import glob

from pyrevit import forms


PROJECTS_ROOT = os.path.realpath(r"//SPR-NAS/Company/Projects")


def get_swe_project_number(doc):
    if not doc:
        return None

    try:
        project_info = doc.ProjectInformation
        for param in project_info.Parameters:
            try:
                if param.Definition and param.Definition.Name == "SWE Project Number":
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


def get_project_root(doc):
    project_number = get_swe_project_number(doc)
    if not project_number:
        return None
    return os.path.join(PROJECTS_ROOT, project_number)


def get_cad_folder(doc):
    project_root = get_project_root(doc)
    if not project_root or not os.path.exists(project_root):
        return None

    matches = [
        p for p in glob.glob(os.path.join(project_root, "10 CAD*"))
        if os.path.isdir(p)
    ]

    if not matches:
        return None

    matches.sort()
    return matches[0]


def pick_folder():
    folder = forms.pick_folder()
    if folder and os.path.isdir(folder):
        return folder
    return None


def get_storage_folder(doc, prompt_user=True):
    cad_folder = get_cad_folder(doc)
    if cad_folder:
        return cad_folder

    if not prompt_user:
        return None

    forms.alert(
        "No SWE Project Number or 10 CAD folder was found.\n"
        "Please select a folder for the dashboard files.",
        warn_icon=False
    )

    return pick_folder()


def get_project_json_path(doc, filename, prompt_user=True):
    folder = get_storage_folder(doc, prompt_user=prompt_user)
    if not folder:
        return None
    return os.path.join(folder, filename)


def get_dashboard_json_path(doc, prompt_user=True):
    title = doc.Title if doc else "Project"
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title)
    return get_project_json_path(doc, safe + "_coordination_dashboard.json", prompt_user=prompt_user)


def get_sync_queue_json_path(doc, prompt_user=True):
    return get_project_json_path(doc, "sync_queue.json", prompt_user=prompt_user)
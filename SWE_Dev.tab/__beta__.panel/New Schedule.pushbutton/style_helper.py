# -*- coding: utf-8 -*-
# ==================== IMPORTS ====================
import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import *
from pyrevit import revit, forms


# ==================== HELPERS ====================
def fmt_color(c):
    try:
        return "RGB({}, {}, {})".format(c.Red, c.Green, c.Blue)
    except:
        return "N/A"


def print_style(style, indent="    "):
    if style is None:
        print("{}[No style]".format(indent))
        return
    try:
        opts = style.GetCellStyleOverrideOptions()
    except:
        opts = None

    props = [
        ("Bold",            style.IsFontBold),
        ("Italic",          style.IsFontItalic),
        ("Underline",       style.IsFontUnderline),
        ("TextSize",        style.TextSize),
        ("FontName",        style.FontName),
        ("BackgroundColor", fmt_color(style.BackgroundColor)),
        ("TextColor",       fmt_color(style.TextColor)),
        ("HorizAlignment",  style.FontHorizontalAlignment),
    ]
    for label, val in props:
        print("{}  {:20}: {}".format(indent, label, val))

    if opts:
        print("{}  [Overrides]".format(indent))
        override_props = [
            ("Bold",            opts.Bold),
            ("Italics",         opts.Italics),
            ("Underline",       opts.Underline),
            ("FontSize",        opts.FontSize),
            ("BackgroundColor", opts.BackgroundColor),
            ("HorizAlignment",  opts.HorizontalAlignment),
        ]
        for label, val in override_props:
            print("{}    {:20}: {}".format(indent, label, val))


# ==================== BUILD STYLE (fresh) ====================
def build_style(bold=False, italic=False, font_size=None, h_align=None):
    """
    Creates a fully fresh TableCellStyle with no inheritance from
    any existing cell. Only explicitly provided values are set.
    """
    style = TableCellStyle()
    opts  = TableCellStyleOverrideOptions()

    opts.Bold    = True
    opts.Italics = True
    style.IsFontBold   = bold
    style.IsFontItalic = italic

    if font_size is not None:
        opts.FontSize  = True
        style.TextSize = font_size

    if h_align is not None:
        align_map = {
            "Left":   HorizontalAlignmentStyle.Left,
            "Center": HorizontalAlignmentStyle.Center,
            "Right":  HorizontalAlignmentStyle.Right,
        }
        resolved = align_map.get(h_align)
        if resolved is None:
            raise ValueError("h_align must be 'Left', 'Center', or 'Right'. Got: '{}'".format(h_align))
        opts.HorizontalAlignment      = True
        style.FontHorizontalAlignment = resolved

    style.SetCellStyleOverrideOptions(opts)
    return style


# ==================== MERGE STYLE (preserve existing) ====================
def merge_style(existing, bold=None, italic=None, font_size=None, h_align=None):
    """
    Creates a new TableCellStyle seeded from `existing`, only
    overwriting properties that are explicitly provided (not None).
    """
    style = TableCellStyle()
    opts  = TableCellStyleOverrideOptions()

    # --- Seed from existing style ---
    if existing is not None:
        try: style.IsFontBold              = existing.IsFontBold
        except: pass
        try: style.IsFontItalic            = existing.IsFontItalic
        except: pass
        try: style.IsFontUnderline         = existing.IsFontUnderline
        except: pass
        try: style.TextSize                = existing.TextSize
        except: pass
        try: style.FontName                = existing.FontName
        except: pass
        try: style.BackgroundColor         = existing.BackgroundColor
        except: pass
        try: style.TextColor               = existing.TextColor
        except: pass
        try: style.FontHorizontalAlignment = existing.FontHorizontalAlignment
        except: pass

        try:
            ex_opts = existing.GetCellStyleOverrideOptions()
            if ex_opts is not None:
                try: opts.Bold                = ex_opts.Bold
                except: pass
                try: opts.Italics             = ex_opts.Italics
                except: pass
                try: opts.Underline           = ex_opts.Underline
                except: pass
                try: opts.FontSize            = ex_opts.FontSize
                except: pass
                try: opts.BackgroundColor     = ex_opts.BackgroundColor
                except: pass
                try: opts.HorizontalAlignment = ex_opts.HorizontalAlignment
                except: pass
        except: pass

    # --- Apply only explicitly provided overrides ---
    if bold is not None:
        opts.Bold        = True
        style.IsFontBold = bold

    if italic is not None:
        opts.Italics       = True
        style.IsFontItalic = italic

    if font_size is not None:
        opts.FontSize  = True
        style.TextSize = font_size

    if h_align is not None:
        align_map = {
            "Left":   HorizontalAlignmentStyle.Left,
            "Center": HorizontalAlignmentStyle.Center,
            "Right":  HorizontalAlignmentStyle.Right,
        }
        resolved = align_map.get(h_align)
        if resolved is None:
            raise ValueError("h_align must be 'Left', 'Center', or 'Right'. Got: '{}'".format(h_align))
        opts.HorizontalAlignment      = True
        style.FontHorizontalAlignment = resolved

    style.SetCellStyleOverrideOptions(opts)
    return style


# ==================== SNAPSHOT ====================
def snapshot_schedule_styles(schedule):
    """
    Captures all existing TableCellStyles and GroupHeaders into a dict:
    {
        "name":          str,
        "sections":      { SectionType: { (row, col): { ... } } },
        "fields":        { i: { "name": str, "style": TableCellStyle } },
        "group_headers": [ { "top", "left", "bottom", "right", "caption" } ]
    }
    """
    snapshot = {
        "name":          schedule.Name,
        "sections":      {},
        "fields":        {},
        "group_headers": [],
    }

    table_data = schedule.GetTableData()

    # --- Sections ---
    for section_type in [SectionType.Header, SectionType.Body, SectionType.Footer]:
        tsd = None
        try:
            tsd = table_data.GetSectionData(section_type)
        except:
            pass
        if tsd is None:
            continue

        section_data = {}
        for row in range(tsd.FirstRowNumber, tsd.LastRowNumber + 1):
            for col in range(tsd.FirstColumnNumber, tsd.LastColumnNumber + 1):
                cell = {
                    "allow_override": False,
                    "style":          None,
                    "merged_cell":    None,
                    "cell_text":      None,
                }
                try: cell["allow_override"] = tsd.AllowOverrideCellStyle(row, col)
                except: pass
                try: cell["style"]          = tsd.GetTableCellStyle(row, col)
                except: pass
                try:
                    m = tsd.GetMergedCell(row, col)
                    cell["merged_cell"] = (m.Top, m.Left, m.Bottom, m.Right)
                except: pass
                try: cell["cell_text"]      = tsd.GetCellText(row, col)
                except: pass
                section_data[(row, col)] = cell

        snapshot["sections"][section_type] = section_data

    # --- Fields ---
    definition = schedule.Definition
    for i in range(definition.GetFieldCount()):
        field_data = {"name": None, "style": None}
        try:
            field              = definition.GetField(i)
            field_data["name"] = field.GetName()
            field_data["style"]= field.GetStyle()
        except: pass
        snapshot["fields"][i] = field_data

    # --- Group Headers (merged multi-cell spans in Body section) ---
    tsd_body = None
    try:
        tsd_body = table_data.GetSectionData(SectionType.Body)
    except:
        pass

    if tsd_body is not None:
        seen = set()
        for row in range(tsd_body.FirstRowNumber, tsd_body.LastRowNumber + 1):
            for col in range(tsd_body.FirstColumnNumber, tsd_body.LastColumnNumber + 1):
                try:
                    m   = tsd_body.GetMergedCell(row, col)
                    key = (m.Top, m.Left, m.Bottom, m.Right)
                    if key in seen:
                        continue
                    seen.add(key)
                    if m.Left != m.Right or m.Top != m.Bottom:
                        caption = None
                        try: caption = tsd_body.GetCellText(m.Top, m.Left)
                        except: pass
                        snapshot["group_headers"].append({
                            "top":     m.Top,
                            "left":    m.Left,
                            "bottom":  m.Bottom,
                            "right":   m.Right,
                            "caption": caption,
                        })
                except: pass

    return snapshot


def print_snapshot(snapshot):
    """Pretty-prints a snapshot dict produced by snapshot_schedule_styles()."""
    print("\n{}\nSnapshot: {}\n{}".format("=" * 50, snapshot["name"], "=" * 50))

    for section_type, cells in snapshot["sections"].items():
        print("\n  [Section: {}]".format(section_type))
        for (row, col), cell in cells.items():
            print("\n    Cell ({}, {})  AllowOverride: {}  Text: '{}'".format(
                row, col,
                cell["allow_override"],
                cell["cell_text"] or ""
            ))
            if cell["merged_cell"]:
                print("      MergedCell: top={} left={} bottom={} right={}".format(
                    *cell["merged_cell"]
                ))
            print_style(cell["style"], indent="      ")

    print("\n  [Fields]")
    for i, field_data in snapshot["fields"].items():
        print("\n    Field [{}]: {}".format(i, field_data["name"]))
        print_style(field_data["style"], indent="      ")

    print("\n  [Group Headers]")
    if snapshot["group_headers"]:
        for gh in snapshot["group_headers"]:
            print("    Rows {}-{}  Cols {}-{}  Caption: '{}'".format(
                gh["top"], gh["bottom"],
                gh["left"], gh["right"],
                gh["caption"] or ""
            ))
    else:
        print("    None found.")


# ==================== READ ====================
def read_schedule_styles(schedule):
    print("\n{}\nSchedule: {}\n{}".format("=" * 50, schedule.Name, "=" * 50))
    table_data = schedule.GetTableData()

    for section_type in [SectionType.Header, SectionType.Body, SectionType.Footer]:
        tsd = None
        try:
            tsd = table_data.GetSectionData(section_type)
        except:
            pass

        if tsd is None:
            print("\n  [{}] Not present".format(section_type))
            continue

        print("\n  [{}]  {} row(s) x {} col(s)".format(
            section_type, tsd.NumberOfRows, tsd.NumberOfColumns))

        for row in range(tsd.FirstRowNumber, tsd.LastRowNumber + 1):
            for col in range(tsd.FirstColumnNumber, tsd.LastColumnNumber + 1):
                allow = tsd.AllowOverrideCellStyle(row, col)
                print("\n    Cell ({}, {})  AllowOverride: {}".format(row, col, allow))
                try:
                    print_style(tsd.GetTableCellStyle(row, col))
                except Exception as e:
                    print("      ERROR: {}".format(e))

    # --- Group Headers ---
    tsd_body = None
    try:
        tsd_body = table_data.GetSectionData(SectionType.Body)
    except:
        pass

    print("\n  [Group Headers]")
    if tsd_body is not None:
        seen = set()
        for row in range(tsd_body.FirstRowNumber, tsd_body.LastRowNumber + 1):
            for col in range(tsd_body.FirstColumnNumber, tsd_body.LastColumnNumber + 1):
                try:
                    m   = tsd_body.GetMergedCell(row, col)
                    key = (m.Top, m.Left, m.Bottom, m.Right)
                    if key in seen:
                        continue
                    seen.add(key)
                    if m.Left != m.Right or m.Top != m.Bottom:
                        caption = None
                        try: caption = tsd_body.GetCellText(m.Top, m.Left)
                        except: pass
                        print("    Rows {}-{}  Cols {}-{}  Caption: '{}'".format(
                            m.Top, m.Bottom, m.Left, m.Right, caption or ""
                        ))
                except Exception as e:
                    print("    GetMergedCell ({}, {}) ERROR: {}".format(row, col, e))
    else:
        print("    Body section not available.")

    # --- Field Styles ---
    print("\n  [Field Styles]")
    definition = schedule.Definition
    for i in range(definition.GetFieldCount()):
        try:
            field = definition.GetField(i)
            print("\n    Field [{}]: {}".format(i, field.GetName()))
            print_style(field.GetStyle())
        except Exception as e:
            print("    Field [{}] ERROR: {}".format(i, e))


# ==================== APPLY ====================
def apply_schedule_styles(schedule, skip_sections=None):
    """
    skip_sections: set of section names to leave untouched.
    Valid values: "title", "subtitle", "headers", "body"

    Example:
        apply_schedule_styles(schedule, skip_sections={"title", "headers"})
    """
    skip = set(s.lower() for s in skip_sections) if skip_sections else set()
    table_data = schedule.GetTableData()

    def get_existing_section_style(tsd, row, col):
        try:
            return tsd.GetTableCellStyle(row, col)
        except:
            return None

    def apply_section(section_type, skip_first_row=False, **kwargs):
        tsd = None
        try:
            tsd = table_data.GetSectionData(section_type)
        except:
            pass
        if tsd is None:
            return
        row_start = tsd.FirstRowNumber + (1 if skip_first_row else 0)
        for row in range(row_start, tsd.LastRowNumber + 1):
            for col in range(tsd.FirstColumnNumber, tsd.LastColumnNumber + 1):
                if not tsd.AllowOverrideCellStyle(row, col):
                    continue
                existing = get_existing_section_style(tsd, row, col)
                tsd.SetCellStyle(row, col, merge_style(existing, **kwargs))

    # Title = first row of Header section
    tsd_header = None
    try:
        tsd_header = table_data.GetSectionData(SectionType.Header)
    except:
        pass

    if tsd_header is not None and "title" not in skip:
        row, col = tsd_header.FirstRowNumber, tsd_header.FirstColumnNumber
        if tsd_header.AllowOverrideCellStyle(row, col):
            existing = get_existing_section_style(tsd_header, row, col)
            tsd_header.SetCellStyle(row, col, merge_style(
                existing, bold=False, italic=False, font_size=24, h_align="Center"
            ))

    if "subtitle" not in skip:
        apply_section(SectionType.Header, skip_first_row=True,
                      bold=False, italic=False, font_size=9, h_align="Left")

    if "headers" not in skip:
        apply_section(SectionType.Body,
                      bold=True, italic=True, font_size=9, h_align="Center")

    if "body" not in skip:
        definition = schedule.Definition
        for i in range(definition.GetFieldCount()):
            try:
                field    = definition.GetField(i)
                existing = None
                try: existing = field.GetStyle()
                except: pass
                field.SetStyle(merge_style(
                    existing, bold=False, italic=False, font_size=9, h_align="Left"
                ))
            except Exception as e:
                print("  Field [{}] style error: {}".format(i, e))


# ==================== MAIN ====================
selected_schedules = forms.select_schedules()

if selected_schedules:
    snapshots_before = [snapshot_schedule_styles(s) for s in selected_schedules]
    for snap in snapshots_before:
        print_snapshot(snap)

    with revit.Transaction("Apply TableCellStyle to Schedules"):
        for s in selected_schedules:
            apply_schedule_styles(s, skip_sections={"subtitle"})

    snapshots_after = [snapshot_schedule_styles(s) for s in selected_schedules]
    for snap in snapshots_after:
        print_snapshot(snap)

    TaskDialog.Show("Done", "Styles applied to {} schedule(s).".format(len(selected_schedules)))
else:
    TaskDialog.Show("Cancelled", "No schedules selected.")

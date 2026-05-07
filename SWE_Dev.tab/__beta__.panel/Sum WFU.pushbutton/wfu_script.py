# -*- coding: utf-8 -*-
"""
WFU to GPM Lookup - native WPF chart window embedded in pyRevit.
Sums WFU from selected plumbing fixtures, then displays Hunter's
Method lookup curves in a resizable WPF window with a live marker.
"""
__title__ = "Sum WFU\n& GPM"
__doc__   = ("Sums WFU from selected plumbing fixtures and shows "
             "the Hunter's Method GPM lookup curve in a WPF window.")

# -- CLR / WPF references ------------------------------------------
import clr
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference("System.Xaml")
clr.AddReference("System.Data")

from pyrevit import revit, DB, forms, script
from Autodesk.Revit.UI.Selection import ISelectionFilter, ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException

from System.Windows import (
    Window, Thickness, Point, CornerRadius,
    HorizontalAlignment, VerticalAlignment,
    FontWeights, WindowStartupLocation, GridLength, GridUnitType,
)
from System.Windows.Controls import (
    Canvas, Grid, StackPanel, Border, DockPanel, TextBlock,
    TextBox, Button, RowDefinition, ColumnDefinition, Orientation,
    DataGrid, DataGridLength, DataGridLengthUnitType,
    DataGridGridLinesVisibility, DataGridHeadersVisibility,
    DataGridSelectionMode, GridSplitter, ScrollViewer,
    ScrollBarVisibility, ComboBox,
)
from System.Windows.Media import (
    SolidColorBrush, Color, Colors, FontFamily,
    PointCollection, DoubleCollection, RotateTransform,
    PenLineJoin,
)
from System.Windows.Shapes import Line, Polyline, Ellipse, Rectangle
from System.Windows.Input import Cursors
from System import EventHandler
from System.Data import DataTable

output = script.get_output()

# -- Color palette (Nexus warm beige + teal/orange accents) --------
def _c(r, g, b, a=255): return Color.FromArgb(a, r, g, b)
def _br(r, g, b, a=255): return SolidColorBrush(_c(r, g, b, a))

C_BG          = _c(247, 246, 242)
C_SURFACE     = _c(249, 248, 245)
C_SURFACE_OFF = _c(243, 240, 236)
C_BORDER      = _c(212, 209, 202)
C_DIVIDER     = _c(220, 217, 213)
C_TEXT        = _c( 40,  37,  29)
C_TEXT_MUTED  = _c(122, 121, 116)
C_TEXT_FAINT  = _c(176, 174, 170)
C_FVT         = _c(  1, 105, 111)   # teal
C_FMV         = _c(218, 113,   1)   # orange
C_MARKER      = _c(161,  44, 123)   # marker purple

# -- Lookup table  (GPM, FVT_WFU, FMV_WFU) ------------------------
_TABLE = [
    ( 1,   0,None),( 2,   1,None),( 3,   3,None),( 4,   4,None),
    ( 5,   6,None),( 6,   7,None),( 7,   8,None),( 8,  10,None),
    ( 9,  12,None),(10,  13,None),(11,  15,None),(12,  16,None),
    (13,  18,None),(14,  20,None),(15,  21,None),(16,  23,None),
    (17,  24,None),(18,  26,None),(19,  28,None),(20,  30,None),
    (21,  32,None),(22,  34,   5),(23,  36,   6),(24,  39,   7),
    (25,  42,   8),(26,  44,   9),(27,  46,  10),(28,  49,  11),
    (29,  51,  12),(30,  54,  13),(31,  56,  14),(32,  58,  15),
    (33,  60,  16),(34,  63,  18),(35,  66,  20),(36,  69,  21),
    (37,  74,  23),(38,  78,  25),(39,  83,  26),(40,  86,  28),
    (41,  90,  30),(42,  95,  31),(43,  99,  33),(44, 103,  35),
    (45, 107,  37),(46, 111,  39),(47, 115,  42),(48, 119,  44),
    (49, 123,  46),(50, 127,  48),(51, 130,  50),(52, 135,  52),
    (53, 141,  54),(54, 146,  57),(55, 151,  60),(56, 155,  63),
    (57, 160,  66),(58, 165,  69),(59, 170,  73),(60, 175,  76),
    (62, 185,  82),(64, 195,  88),(66, 205,  95),(68, 215, 102),
    (70, 225, 108),(72, 236, 116),(74, 245, 124),(76, 254, 132),
    (78, 264, 140),(80, 275, 148),(82, 284, 158),(84, 294, 168),
    (86, 305, 176),(88, 315, 186),(90, 325, 195),(92, 337, 205),
    (94, 348, 214),(96, 359, 223),(98, 370, 234),(100,380, 245),
    (105,406, 270),(110,431, 295),(115,455, 329),(120,479, 365),
    (125,506, 396),(130,533, 430),(135,559, 460),(140,585, 490),
    (145,611, 521),(150,638, 559),(155,665, 596),(160,692, 631),
    (165,719, 666),(170,748, 700),(175,778, 739),(180,809, 775),
    (185,840, 811),(190,874, 850),(200,945, 931),(210,1018,1009),
    (220,1091,1091),(230,1173,1173),(240,1254,1254),(250,1335,1335),
    (260,1418,1418),(270,1500,1500),(280,1598,1598),(290,1668,1668),
    (300,1755,1755),(310,1845,1845),(320,1926,1926),(330,2018,2018),
    (340,2110,2110),(350,2204,2204),(360,2298,2298),(370,2388,2388),
    (380,2480,2480),(390,2575,2575),(400,2670,2670),(410,2765,2765),
    (420,2862,2862),(430,2960,2960),(440,3060,3060),(450,3150,3150),
    (500,3620,3620),
]

_FVT = [(wfu, gpm) for gpm, wfu, _   in _TABLE]
_FMV = [(wfu, gpm) for gpm, _,   wfu in _TABLE if wfu is not None]
MAX_WFU = float(_FVT[-1][0])   # 3620
MAX_GPM = 500.0

def interp_gpm(wfu, pairs):
    """Return (gpm_float, note_str) for a given WFU via linear interpolation."""
    if wfu is None or wfu <= 0:
        return None, ""
    if wfu <= pairs[0][0]:
        return float(pairs[0][1]), "at minimum"
    if wfu >= pairs[-1][0]:
        return float(pairs[-1][1]), "at/above max"
    for i in range(len(pairs) - 1):
        w0, g0 = pairs[i];  w1, g1 = pairs[i + 1]
        if w0 <= wfu <= w1:
            r = (wfu - w0) / float(w1 - w0)
            return g0 + r * (g1 - g0), "interpolated"
    return None, ""


# -- Revit helpers -------------------------------------------------
WFU_PARAM_NAMES  = ["WFU", "Water Fixture Units", "Fixture Units", "FU"]
PLUMBING_CAT_ID  = int(DB.BuiltInCategory.OST_PlumbingFixtures)
doc   = revit.doc
uidoc = revit.uidoc

def _read_param(el, name):
    p = el.LookupParameter(name)
    if p and p.HasValue:
        if p.StorageType == DB.StorageType.Double:  return p.AsDouble()
        if p.StorageType == DB.StorageType.Integer: return float(p.AsInteger())
    return None

def get_wfu(fix):
    for n in WFU_PARAM_NAMES:
        v = _read_param(fix, n)
        if v is not None: return v
    tid = fix.GetTypeId()
    if tid and tid != DB.ElementId.InvalidElementId:
        t = doc.GetElement(tid)
        if t:
            for n in WFU_PARAM_NAMES:
                v = _read_param(t, n)
                if v is not None: return v
    return None

class PlumbingFixtureFilter(ISelectionFilter):
    """Restricts interactive selection to OST_PlumbingFixtures only."""
    def AllowElement(self, element):
        cat = element.Category
        return cat is not None and cat.Id.IntegerValue == PLUMBING_CAT_ID

    def AllowReference(self, reference, position):
        return False


def collect_wfu():
    """Return (total_wfu, fixture_count, missing_count, detail_rows)."""
    sel_ids = list(uidoc.Selection.GetElementIds())
    if not sel_ids:
        # Nothing pre-selected -- let user pick interactively
        try:
            refs = uidoc.Selection.PickObjects(
                ObjectType.Element,
                PlumbingFixtureFilter(),
                "Select plumbing fixtures  --  press Finish (green check) when done"
            )
            sel_ids = [r.ElementId for r in refs]
        except OperationCanceledException:
            forms.alert("Selection cancelled.",
                        title="Sum WFU & GPM", exitscript=True)
    if not sel_ids:
        forms.alert("No fixtures selected.",
                    title="Sum WFU & GPM", exitscript=True)

    total = 0.0
    found, missing = [], []
    for eid in sel_ids:
        el = doc.GetElement(eid)
        if el is None: continue
        cat = el.Category
        if not (cat and cat.Id.IntegerValue == PLUMBING_CAT_ID): continue
        wfu = get_wfu(el)
        try:    fam  = el.Symbol.Family.Name
        except: fam  = ""
        try:    typ  = el.Symbol.Name
        except:
            try:    typ = el.Name
            except: typ = str(el.Id)
        if wfu is not None:
            total += wfu
            found.append((el.Id.IntegerValue, fam, typ, wfu))
        else:
            missing.append((el.Id.IntegerValue, fam, typ))

    if not found and not missing:
        forms.alert("No plumbing fixtures found in selection.",
                    title="Sum WFU & GPM", exitscript=True)
    # Group by (family, type, wfu_each) for the DataGrid
    from collections import defaultdict
    groups = defaultdict(lambda: [0, 0.0])
    for eid, fam, typ, wfu in found:
        key = (fam, typ, float(wfu))
        groups[key][0] += 1
        groups[key][1] += float(wfu)
    grouped = sorted(
        [(fam, typ, wfu_e, d[0], d[1]) for (fam, typ, wfu_e), d in groups.items()],
        key=lambda r: (-r[4], r[0], r[1])
    )
    return total, len(found), len(missing), found, missing, grouped

# Run collection
total_wfu, fixture_count, missing_count, found_rows, missing_rows, grouped_rows = collect_wfu()
fvt_gpm, fvt_note = interp_gpm(total_wfu, _FVT)
fmv_gpm, fmv_note = interp_gpm(total_wfu, _FMV)

# # Output text summary to pyRevit panel
# output.print_md("# WFU to GPM Summary")
# output.print_md("| Metric | Value |")
# output.print_md("|--------|-------|")
# output.print_md("| Total WFU | **{}** |".format(
#     int(total_wfu) if total_wfu == int(total_wfu) else round(total_wfu, 2)))
# if fvt_gpm:
#     output.print_md("| FVT Design GPM | **{:.1f} GPM** ({}) |".format(fvt_gpm, fvt_note))
# if fmv_gpm:
#     output.print_md("| FMV Design GPM | **{:.1f} GPM** ({}) |".format(fmv_gpm, fmv_note))
# output.print_md("| Fixtures counted | {} |".format(fixture_count))
# if missing_count:
#     output.print_md("| Missing WFU param | {} |".format(missing_count))
# if found_rows:
#     output.print_md("\n### Fixture Detail\n")
#     output.print_md("| Element ID | Family | Type | WFU |")
#     output.print_md("|-----------|--------|------|-----|")
#     for eid, fam, typ, wfu in sorted(found_rows, key=lambda r: (r[1], r[2])):
#         output.print_md("| {} | {} | {} | {} |".format(
#             eid, fam, typ,
#             int(wfu) if wfu == int(wfu) else round(wfu, 2)))


# -- WPF window helper utilities -----------------------------------
def _br(r, g, b, a=255):
    return SolidColorBrush(_c(r, g, b, a))

def _lbl(text, size=12, color=None, weight=None, margin=None):
    tb = TextBlock()
    tb.Text = text
    tb.FontSize = size
    if color:  tb.Foreground = color
    if weight: tb.FontWeight = weight
    if margin: tb.Margin = margin
    return tb

def _row(h="Auto"):
    r = RowDefinition()
    if h == "Auto":
        r.Height = GridLength.Auto
    elif isinstance(h, str) and h.endswith("*"):
        r.Height = GridLength(float(h[:-1]) if h[:-1] else 1, GridUnitType.Star)
    elif h == "*":
        r.Height = GridLength(1, GridUnitType.Star)
    else:
        r.Height = GridLength(float(h))
    return r

def _col(w="Auto"):
    c = ColumnDefinition()
    c.Width = GridLength.Auto if w == "Auto" else GridLength(1, GridUnitType.Star)
    return c

def _btn(text, tag):
    b = Button()
    b.Content = text
    b.Tag = tag
    b.Padding = Thickness(11, 5, 11, 5)
    b.BorderThickness = Thickness(1)
    b.FontSize = 12
    b.Cursor = Cursors.Hand
    return b

def _style_btn_inactive(b):
    b.Background  = _br(249, 248, 245)
    b.Foreground  = _br(122, 121, 116)
    b.BorderBrush = _br(212, 209, 202)

def _style_btn_active(b, system):
    if system == "fvt":
        b.Background  = _br(1, 105, 111, 28)
        b.Foreground  = _br(1, 105, 111)
        b.BorderBrush = _br(1, 105, 111)
    elif system == "fmv":
        b.Background  = _br(218, 113, 1, 28)
        b.Foreground  = _br(218, 113, 1)
        b.BorderBrush = _br(218, 113, 1)
    else:
        b.Background  = _br(206, 220, 216)
        b.Foreground  = _br(1, 105, 111)
        b.BorderBrush = _br(1, 105, 111)

def _bordered(child, bg, border_color, padding, corner=6, margin=None):
    bdr = Border()
    bdr.Background    = bg if isinstance(bg, SolidColorBrush) else _br(*bg)
    bdr.BorderBrush   = border_color if isinstance(border_color, SolidColorBrush) else _br(*border_color)
    bdr.BorderThickness = Thickness(1)
    bdr.CornerRadius  = CornerRadius(corner)
    bdr.Padding       = padding
    if margin: bdr.Margin = margin
    bdr.Child = child
    return bdr


import math as _math

# Pipe material data: name -> {v_min, v_max (ft/s), sizes: [(label, ID_inches)]}
# PIPE_DATA: (name, v_min ft/s, v_max ft/s, sizes [(label, ID_in)], HW_C_factor)
PIPE_DATA = [
    ("Copper Type L",    2.0, 8.0, [
        ('1/2"', 0.545), ('3/4"', 0.785), ('1"',    1.025),
        ('1-1/4"', 1.265), ('1-1/2"', 1.505), ('2"', 1.985),
        ('2-1/2"', 2.465), ('3"', 2.945), ('4"', 3.905)], 130),
    ("Copper Type M",    2.0, 8.0, [
        ('1/2"', 0.569), ('3/4"', 0.811), ('1"',    1.055),
        ('1-1/4"', 1.291), ('1-1/2"', 1.527), ('2"', 2.009),
        ('2-1/2"', 2.495), ('3"', 2.981)], 130),
    ("Copper Type K",    2.0, 8.0, [
        ('1/2"', 0.527), ('3/4"', 0.745), ('1"',    0.995),
        ('1-1/4"', 1.245), ('1-1/2"', 1.481), ('2"', 1.959),
        ('2-1/2"', 2.435), ('3"', 2.907), ('4"', 3.857)], 130),
    ("PVC Schedule 40",  2.0, 8.0, [
        ('1/2"', 0.622), ('3/4"', 0.824), ('1"',    1.049),
        ('1-1/4"', 1.380), ('1-1/2"', 1.610), ('2"', 2.067),
        ('2-1/2"', 2.469), ('3"', 3.068), ('4"', 4.026), ('6"', 6.065)], 150),
    ("PVC Schedule 80",  2.0, 8.0, [
        ('1/2"', 0.546), ('3/4"', 0.742), ('1"',    0.957),
        ('1-1/4"', 1.278), ('1-1/2"', 1.500), ('2"', 1.913),
        ('3"', 2.900), ('4"', 3.826)], 150),
    ("IPEX CPVC Schedule 40", 1.0, 8.0, [
        ('1/2"', 0.526), ('3/4"', 0.722), ('1"',    0.936),
        ('1-1/4"', 1.255), ('1-1/2"', 1.476), ('2"', 1.913),
        ('2-1/2"', 2.290), ('3"', 2.864)], 150),
    ("CPVC Schedule 40", 1.0, 5.0, [
        ('1/2"', 0.622), ('3/4"', 0.824), ('1"',    1.049),
        ('1-1/4"', 1.380), ('1-1/2"', 1.610), ('2"', 2.067)], 150),
    ("PEX CTS SDR-9",    2.0, 8.0, [
        ('1/2"', 0.475), ('3/4"', 0.671), ('1"',    0.884),
        ('1-1/4"', 1.107), ('1-1/2"', 1.330), ('2"', 1.770)], 150),
    ("Galv. Steel Sch.40", 2.0, 8.0, [
        ('1/2"', 0.622), ('3/4"', 0.824), ('1"',    1.049),
        ('1-1/4"', 1.380), ('1-1/2"', 1.610), ('2"', 2.067),
        ('2-1/2"', 2.469), ('3"', 3.068), ('4"', 4.026)], 120),
    ("Cast Iron",        2.0, 6.0, [
        ('2"', 2.067), ('3"', 3.068), ('4"', 4.026),
        ('6"', 6.065), ('8"', 7.981)], 100),
]

# helper: (name, v_min, v_max, sizes) by name
def _pipe_entry(name):
    for row in PIPE_DATA:
        if row[0] == name:
            return row
    return None


def calc_velocity(gpm, id_in):
    """Flow velocity (ft/s) given GPM and pipe inside diameter in inches."""
    if not gpm or gpm <= 0 or id_in <= 0:
        return None
    r_ft    = (id_in / 2.0) / 12.0
    area    = _math.pi * r_ft * r_ft
    q_ft3s  = gpm * 0.002228          # 1 US GPM = 0.002228 ft3/s
    return q_ft3s / area


def velocity_status(vel, v_min, v_max):
    """Return (label, R, G, B) describing velocity vs. recommended range."""
    if vel is None:
        return ("--", 186, 185, 180)
    tol = 0.05 * (v_max - v_min)      # 5% tolerance band at each limit
    if vel < v_min - tol:
        return ("Low", 218, 113, 1)    # orange
    if vel > v_max + tol:
        return ("High", 161, 44, 123)  # error maroon
    if vel < v_min or vel > v_max:
        return ("Borderline", 218, 113, 1)
    return ("OK", 67, 122, 34)         # success green

def calc_pressure_drop(gpm, id_in, c_factor):
    """Hazen-Williams pressure drop in PSI per 100 ft.
    Q in GPM, id_in = inside diameter (inches), c_factor = H-W C.
    Formula: 0.2083 * (100/C)^1.852 * Q^1.852 / d^4.87 * 0.4335
    where 0.2083*(100/C)^1.852*Q^1.852/d^4.87 gives ft head loss per 100 ft,
    and 0.4335 converts ft of head to PSI (1 ft H2O = 0.4335 PSI).
    """
    if not gpm or gpm <= 0 or id_in <= 0 or c_factor <= 0:
        return None
    try:
        return 0.2083 * ((100.0 / c_factor) ** 1.852) * (gpm ** 1.852) / (id_in ** 4.87) * 0.4335
    except Exception:
        return None


def build_window(init_wfu, init_fvt_gpm, init_fmv_gpm, fixture_count, missing_count, grouped_rows):
    """Construct the full WPF window and return (window, refs_dict)."""

    win = Window()
    win.Title  = "WFU to GPM Lookup  --  Hunter's Method"
    win.Width  = 1060
    win.Height = 660
    win.MinWidth  = 760
    win.MinHeight = 520
    win.Background  = _br(247, 246, 242)
    win.FontFamily  = FontFamily("Segoe UI")
    win.FontSize    = 13
    win.WindowStartupLocation = WindowStartupLocation.CenterScreen

    root = Grid()
    win.Content = root
    root.RowDefinitions.Add(_row("Auto"))   # row 0 -- header
    root.RowDefinitions.Add(_row("Auto"))   # row 1 -- controls
    root.RowDefinitions.Add(_row("Auto"))   # row 2 -- velocity calc
    root.RowDefinitions.Add(_row("3*"))     # row 3 -- chart canvas
    root.RowDefinitions.Add(_row("5"))      # row 4 -- grid splitter
    root.RowDefinitions.Add(_row("1*"))     # row 5 -- fixture breakdown
    root.RowDefinitions.Add(_row("Auto"))   # row 6 -- status bar

    # -- Row 0: Header --------------------------------------------
    hdr = Border()
    hdr.Background     = _br(249, 248, 245)
    hdr.BorderBrush    = _br(220, 217, 213)
    hdr.BorderThickness = Thickness(0, 0, 0, 1)
    hdr.Padding        = Thickness(16, 10, 16, 10)
    Grid.SetRow(hdr, 0)
    root.Children.Add(hdr)

    hdr_grid = Grid()
    hdr_grid.ColumnDefinitions.Add(_col("*"))
    hdr_grid.ColumnDefinitions.Add(_col("Auto"))
    hdr_grid.ColumnDefinitions.Add(_col("Auto"))
    hdr.Child = hdr_grid

    # Title
    title_sp = StackPanel()
    title_sp.Orientation = Orientation.Horizontal
    title_sp.VerticalAlignment = VerticalAlignment.Center
    Grid.SetColumn(title_sp, 0)
    hdr_grid.Children.Add(title_sp)
    t1 = _lbl("WFU to GPM", 15, _br(40, 37, 29), FontWeights.SemiBold, Thickness(0,0,8,0))
    t2 = _lbl("Hunter's Method  |  IPC/ASPE", 11, _br(122, 121, 116))
    title_sp.Children.Add(t1)
    title_sp.Children.Add(t2)

    def _kpi_badge(label_text, init_val, fg_color, col_index):
        outer = StackPanel()
        outer.Orientation = Orientation.Vertical
        outer.Margin = Thickness(8 if col_index == 1 else 0, 0, 0, 0)
        outer.VerticalAlignment = VerticalAlignment.Center
        tag = _lbl(label_text, 9, _br(122, 121, 116), FontWeights.SemiBold,
                   Thickness(0, 0, 0, 1))
        outer.Children.Add(tag)
        val_row = StackPanel()
        val_row.Orientation = Orientation.Horizontal
        val_tb = _lbl(init_val, 17, fg_color, FontWeights.Bold)
        val_row.Children.Add(val_tb)
        val_row.Children.Add(_lbl(" GPM", 10, _br(122, 121, 116),
                                  margin=Thickness(3, 4, 0, 0)))
        outer.Children.Add(val_row)
        bdr = _bordered(outer, (243, 240, 236), (220, 217, 213),
                        Thickness(12, 7, 12, 7), corner=6)
        bdr.VerticalAlignment = VerticalAlignment.Center
        Grid.SetColumn(bdr, col_index)
        hdr_grid.Children.Add(bdr)
        return val_tb

    fvt_val = "--" if init_fvt_gpm is None else "{:.1f}".format(init_fvt_gpm)
    fmv_val = "--" if init_fmv_gpm is None else "{:.1f}".format(init_fmv_gpm)
    fvt_disp = _kpi_badge("FVT", fvt_val, _br(1, 105, 111),  1)
    fmv_disp = _kpi_badge("FMV", fmv_val, _br(218, 113, 1), 2)

    # -- Row 1: Controls ------------------------------------------
    ctrl = Border()
    ctrl.Background     = _br(249, 248, 245)
    ctrl.BorderBrush    = _br(220, 217, 213)
    ctrl.BorderThickness = Thickness(0, 0, 0, 1)
    ctrl.Padding        = Thickness(16, 8, 16, 8)
    Grid.SetRow(ctrl, 1)
    root.Children.Add(ctrl)

    ctrl_grid = Grid()
    ctrl_grid.ColumnDefinitions.Add(_col("Auto"))
    ctrl_grid.ColumnDefinitions.Add(_col("*"))
    ctrl_grid.ColumnDefinitions.Add(_col("Auto"))
    ctrl.Child = ctrl_grid

    # WFU input with label stacked above
    wfu_sp = StackPanel()
    wfu_sp.Orientation = Orientation.Vertical
    wfu_sp.VerticalAlignment = VerticalAlignment.Center
    Grid.SetColumn(wfu_sp, 0)
    ctrl_grid.Children.Add(wfu_sp)
    wfu_sp.Children.Add(_lbl("Water Fixture Units", 9, _br(122, 121, 116),
                             FontWeights.SemiBold, Thickness(1, 0, 0, 2)))
    wfu_inner = StackPanel()
    wfu_inner.Orientation = Orientation.Horizontal
    wfu_box = TextBox()
    wfu_box.Width  = 90
    wfu_box.FontSize   = 17
    wfu_box.FontWeight = FontWeights.Bold
    wfu_box.Padding    = Thickness(8, 5, 8, 5)
    wfu_box.BorderThickness = Thickness(0)
    wfu_box.Background  = _br(255, 255, 255)
    wfu_box.VerticalContentAlignment = VerticalAlignment.Center
    init_str = str(int(init_wfu)) if init_wfu == int(init_wfu) else str(round(init_wfu, 2))
    wfu_box.Text = init_str
    wfu_bdr = _bordered(wfu_box, (255,255,255), (212,209,202),
                        Thickness(0), corner=5)
    wfu_inner.Children.Add(wfu_bdr)
    wfu_inner.Children.Add(_lbl(" WFU", 11, _br(122, 121, 116),
                                margin=Thickness(6, 0, 0, 0)))
    wfu_sp.Children.Add(wfu_inner)

    # Segmented system toggle (border wraps all three buttons flush)
    toggle_outer = StackPanel()
    toggle_outer.Orientation = Orientation.Vertical
    toggle_outer.VerticalAlignment = VerticalAlignment.Center
    Grid.SetColumn(toggle_outer, 2)
    ctrl_grid.Children.Add(toggle_outer)
    toggle_outer.Children.Add(_lbl("System Type", 9, _br(122, 121, 116),
                                   FontWeights.SemiBold, Thickness(0, 0, 0, 2)))
    toggle_row = StackPanel()
    toggle_row.Orientation = Orientation.Horizontal
    toggle_outer.Children.Add(toggle_row)
    btn_fvt  = _btn("Flush Valve Tanks",   "fvt")
    btn_fmv  = _btn("Flushometer Valves",  "fmv")
    btn_both = _btn("Both",                "both")
    btn_fvt.Margin  = Thickness(0, 0, 4, 0)
    btn_fmv.Margin  = Thickness(0, 0, 4, 0)
    toggle_row.Children.Add(btn_fvt)
    toggle_row.Children.Add(btn_fmv)
    toggle_row.Children.Add(btn_both)

    # -- Row 2: Chart Canvas ---------------------------------------
    chart_canvas = Canvas()
    chart_canvas.Background = _br(255, 255, 255)
    chart_canvas.Margin     = Thickness(0)
    Grid.SetRow(chart_canvas, 3)
    root.Children.Add(chart_canvas)

    # -- Row 2: Pipe Calculator (inputs left | results right) ------------
    vel_bdr = Border()
    vel_bdr.Background      = _br(249, 248, 245)
    vel_bdr.BorderBrush     = _br(220, 217, 213)
    vel_bdr.BorderThickness = Thickness(0, 0, 0, 1)
    vel_bdr.Padding         = Thickness(0)
    Grid.SetRow(vel_bdr, 2)
    root.Children.Add(vel_bdr)

    pipe_outer = Grid()
    pipe_outer.ColumnDefinitions.Add(_col("Auto"))   # inputs
    pipe_outer.ColumnDefinitions.Add(_col("Auto"))   # vertical divider
    pipe_outer.ColumnDefinitions.Add(_col("*"))      # results
    vel_bdr.Child = pipe_outer

    # _vlbl helper (must be defined before any usage below)
    def _vlbl(text, size=11, color=None, margin=None, weight=None):
        tb = TextBlock()
        tb.Text = text
        tb.FontSize = size
        tb.VerticalAlignment = VerticalAlignment.Center
        if color:  tb.Foreground = color
        if weight: tb.FontWeight = weight
        if margin: tb.Margin = margin
        return tb

    # -- LEFT: Inputs panel ----------------------------------------------
    inp_bdr = Border()
    inp_bdr.Background      = _br(243, 240, 236)
    inp_bdr.BorderBrush     = _br(220, 217, 213)
    inp_bdr.BorderThickness = Thickness(0)
    inp_bdr.Padding         = Thickness(16, 10, 20, 10)
    Grid.SetColumn(inp_bdr, 0)
    pipe_outer.Children.Add(inp_bdr)

    inp_stack = StackPanel()
    inp_stack.Orientation = Orientation.Vertical
    inp_bdr.Child = inp_stack

    inp_stack.Children.Add(_vlbl("PIPE CALCULATOR", 9, _br(1, 105, 111),
                                  Thickness(0, 0, 0, 7), FontWeights.SemiBold))

    inp_row1 = StackPanel()
    inp_row1.Orientation = Orientation.Horizontal
    inp_row1.Margin = Thickness(0, 0, 0, 6)
    inp_stack.Children.Add(inp_row1)

    inp_row1.Children.Add(_vlbl("Material", 11, _br(122, 121, 116),
                                 Thickness(0, 0, 6, 0)))
    mat_cb = ComboBox()
    mat_cb.FontSize  = 12
    mat_cb.MinWidth  = 152
    mat_cb.MaxWidth  = 152
    mat_cb.Margin    = Thickness(0, 0, 0, 0)
    mat_cb.VerticalAlignment = VerticalAlignment.Center
    for entry in PIPE_DATA:
        mat_cb.Items.Add(entry[0])
    mat_cb.SelectedIndex = 0
    inp_row1.Children.Add(mat_cb)

    inp_row2 = StackPanel()
    inp_row2.Orientation = Orientation.Horizontal
    inp_stack.Children.Add(inp_row2)

    inp_row2.Children.Add(_vlbl("Nom. Size", 11, _br(122, 121, 116),
                                 Thickness(0, 0, 6, 0)))
    size_cb = ComboBox()
    size_cb.FontSize = 12
    size_cb.MinWidth = 72
    size_cb.MaxWidth = 72
    size_cb.Margin   = Thickness(0, 0, 14, 0)
    size_cb.VerticalAlignment = VerticalAlignment.Center
    inp_row2.Children.Add(size_cb)

    inp_row2.Children.Add(_vlbl("Inside Dia.", 11, _br(122, 121, 116),
                                 Thickness(0, 0, 6, 0)))
    id_tb = TextBox()
    id_tb.Width    = 58
    id_tb.FontSize = 12
    id_tb.FontWeight = FontWeights.SemiBold
    id_tb.Padding  = Thickness(6, 3, 6, 3)
    id_tb.Margin   = Thickness(0, 0, 3, 0)
    id_tb.BorderBrush = _br(212, 209, 202)
    id_tb.VerticalAlignment = VerticalAlignment.Center
    inp_row2.Children.Add(id_tb)
    inp_row2.Children.Add(_vlbl("in", 11, _br(122, 121, 116)))

    dp_cfactor_tb = TextBlock()
    dp_cfactor_tb.FontSize   = 9
    dp_cfactor_tb.Foreground = _br(186, 185, 180)
    dp_cfactor_tb.Margin     = Thickness(0, 6, 0, 0)
    dp_cfactor_tb.Text       = ""
    inp_stack.Children.Add(dp_cfactor_tb)

    # -- Vertical divider ------------------------------------------------
    vdiv = Border()
    vdiv.Width      = 1
    vdiv.Background = _br(220, 217, 213)
    Grid.SetColumn(vdiv, 1)
    pipe_outer.Children.Add(vdiv)

    # -- RIGHT: Results table [metric | FVT col | FMV col] ---------------
    res_bdr = Border()
    res_bdr.Padding = Thickness(20, 10, 20, 10)
    Grid.SetColumn(res_bdr, 2)
    pipe_outer.Children.Add(res_bdr)

    res_stack = StackPanel()
    res_stack.Orientation = Orientation.Vertical
    res_bdr.Child = res_stack

    # Header row: [spacer | FVT | FMV]
    res_hdr = StackPanel()
    res_hdr.Orientation = Orientation.Horizontal
    res_hdr.Margin = Thickness(0, 0, 0, 5)
    res_stack.Children.Add(res_hdr)
    spacer_tb = TextBlock()
    spacer_tb.Width = 72
    res_hdr.Children.Add(spacer_tb)
    fvt_col_lbl = _vlbl("FVT", 10, _br(1, 105, 111), Thickness(0,0,0,0),
                         FontWeights.SemiBold)
    fvt_col_lbl.Width = 140
    res_hdr.Children.Add(fvt_col_lbl)
    res_hdr.Children.Add(_vlbl("FMV", 10, _br(218, 113, 1), Thickness(0,0,0,0),
                                FontWeights.SemiBold))

    # Helper: build a result cell (value + unit + dot + status label)
    def _rcell(unit, col_w=140):
        sp = StackPanel()
        sp.Orientation = Orientation.Horizontal
        sp.VerticalAlignment = VerticalAlignment.Center
        sp.Width = col_w
        val = TextBlock()
        val.FontSize   = 14
        val.FontWeight = FontWeights.SemiBold
        val.Foreground = _br(40, 37, 29)
        val.VerticalAlignment = VerticalAlignment.Center
        val.Margin = Thickness(0, 0, 3, 0)
        val.Text = "--"
        sp.Children.Add(val)
        sp.Children.Add(_vlbl(unit, 10, _br(122, 121, 116),
                               Thickness(0, 0, 7, 0)))
        dot = Ellipse()
        dot.Width  = 8
        dot.Height = 8
        dot.Fill   = _br(186, 185, 180)
        dot.Margin = Thickness(0, 0, 4, 0)
        dot.VerticalAlignment = VerticalAlignment.Center
        sp.Children.Add(dot)
        sts = TextBlock()
        sts.FontSize   = 9
        sts.Foreground = _br(122, 121, 116)
        sts.VerticalAlignment = VerticalAlignment.Center
        sts.Text = ""
        sp.Children.Add(sts)
        return sp, val, dot, sts

    # Helper: pressure-drop cell (value + unit, no dot/status)
    def _dpcell(col_w=140):
        sp = StackPanel()
        sp.Orientation = Orientation.Horizontal
        sp.VerticalAlignment = VerticalAlignment.Center
        sp.Width = col_w
        val = TextBlock()
        val.FontSize   = 14
        val.FontWeight = FontWeights.SemiBold
        val.Foreground = _br(40, 37, 29)
        val.VerticalAlignment = VerticalAlignment.Center
        val.Margin = Thickness(0, 0, 3, 0)
        val.Text = "--"
        sp.Children.Add(val)
        sp.Children.Add(_vlbl("psi/100ft", 10, _br(122, 121, 116)))
        return sp, val

    # Velocity row
    vel_row = StackPanel()
    vel_row.Orientation = Orientation.Horizontal
    vel_row.Margin = Thickness(0, 0, 0, 4)
    res_stack.Children.Add(vel_row)
    vel_metric = _vlbl("Velocity", 10, _br(122, 121, 116), Thickness(0,0,0,0))
    vel_metric.Width = 72
    vel_row.Children.Add(vel_metric)
    fvt_vel_sp, fvt_vel_tb, fvt_vel_dot, fvt_vel_sts = _rcell("ft/s")
    vel_row.Children.Add(fvt_vel_sp)
    fmv_vel_sp, fmv_vel_tb, fmv_vel_dot, fmv_vel_sts = _rcell("ft/s", col_w=160)
    vel_row.Children.Add(fmv_vel_sp)

    # Hazen-Williams pressure-drop row
    dp_row = StackPanel()
    dp_row.Orientation = Orientation.Horizontal
    res_stack.Children.Add(dp_row)
    dp_metric = _vlbl("H-W Press.", 10, _br(122, 121, 116), Thickness(0,0,0,0))
    dp_metric.Width = 72
    dp_row.Children.Add(dp_metric)
    fvt_dp_sp, fvt_dp_tb = _dpcell()
    dp_row.Children.Add(fvt_dp_sp)
    fmv_dp_sp, fmv_dp_tb = _dpcell(col_w=160)
    dp_row.Children.Add(fmv_dp_sp)

    # Footnote: recommended velocity range + GPM context
    vel_range_tb = TextBlock()
    vel_range_tb.FontSize   = 9
    vel_range_tb.Foreground = _br(186, 185, 180)
    vel_range_tb.Margin     = Thickness(0, 6, 0, 0)
    vel_range_tb.Text       = ""
    res_stack.Children.Add(vel_range_tb)

    # Backward-compat aliases
    vel_result_tb = fvt_vel_tb
    vel_dot       = fvt_vel_dot
    vel_status_tb = fvt_vel_sts

    # -- Row 3: GridSplitter ------------------------------------------
    splitter = GridSplitter()
    splitter.Height = 5
    splitter.HorizontalAlignment = HorizontalAlignment.Stretch
    splitter.Background    = _br(220, 217, 213)
    Grid.SetRow(splitter, 4)
    root.Children.Add(splitter)

    # -- Row 4: Fixture Breakdown DataGrid ----------------------------
    dg_border = Border()
    dg_border.Background    = _br(249, 248, 245)
    dg_border.BorderBrush   = _br(220, 217, 213)
    dg_border.BorderThickness = Thickness(0, 0, 0, 0)
    Grid.SetRow(dg_border, 5)
    root.Children.Add(dg_border)

    dg_outer = Grid()
    dg_outer.RowDefinitions.Add(_row("Auto"))
    dg_outer.RowDefinitions.Add(_row("*"))
    dg_border.Child = dg_outer

    # Header strip
    dg_hdr = Border()
    dg_hdr.Background     = _br(243, 240, 236)
    dg_hdr.BorderBrush    = _br(220, 217, 213)
    dg_hdr.BorderThickness = Thickness(0, 0, 0, 1)
    dg_hdr.Padding        = Thickness(14, 5, 14, 5)
    Grid.SetRow(dg_hdr, 0)
    dg_outer.Children.Add(dg_hdr)

    dg_hdr_sp = StackPanel()
    dg_hdr_sp.Orientation = Orientation.Horizontal
    dg_hdr.Child = dg_hdr_sp

    dg_hdr_sp.Children.Add(_lbl("Fixture Breakdown", 11,
        _br(40, 37, 29), FontWeights.SemiBold))
    total_wfu_in_table = sum(r[4] for r in grouped_rows) if grouped_rows else 0
    dg_hdr_sp.Children.Add(_lbl(
        "   {0} type(s)   |   {1:.0f} total WFU".format(
            len(grouped_rows), total_wfu_in_table),
        11, _br(122, 121, 116)))

    # Build DataTable
    dt = DataTable()
    for col_name in ("Family", "Type", "WFU Each", "Count", "WFU Subtotal"):
        dt.Columns.Add(col_name)
    for fam, typ, wfu_e, cnt, wfu_sub in grouped_rows:
        row_data = dt.NewRow()
        row_data["Family"]       = fam if fam else "(unnamed)"
        row_data["Type"]         = typ if typ else "(unnamed)"
        row_data["WFU Each"]     = ("{:.2f}" if wfu_e != int(wfu_e) else "{:.0f}").format(wfu_e)
        row_data["Count"]        = str(cnt)
        row_data["WFU Subtotal"] = ("{:.2f}" if wfu_sub != int(wfu_sub) else "{:.0f}").format(wfu_sub)
        dt.Rows.Add(row_data)

    # DataGrid widget
    dg = DataGrid()
    dg.ItemsSource           = dt.DefaultView
    dg.AutoGenerateColumns   = True
    dg.IsReadOnly            = True
    dg.CanUserAddRows        = False
    dg.CanUserDeleteRows     = False
    dg.CanUserReorderColumns = True
    dg.CanUserResizeColumns  = True
    dg.SelectionMode         = DataGridSelectionMode.Single
    dg.GridLinesVisibility   = DataGridGridLinesVisibility.Horizontal
    dg.HeadersVisibility     = DataGridHeadersVisibility.Column
    dg.RowHeight             = 28
    dg.FontSize              = 12
    dg.Background            = _br(249, 248, 245)
    dg.RowBackground         = _br(255, 255, 255)
    dg.AlternatingRowBackground = _br(247, 246, 242)
    dg.Foreground            = _br(40, 37, 29)
    dg.BorderThickness       = Thickness(0)
    dg.Margin                = Thickness(0)
    dg.HorizontalGridLinesBrush = _br(220, 217, 213)
    dg.ColumnHeaderHeight    = 28

    dg_scroll = ScrollViewer()
    dg_scroll.Content = dg
    dg_scroll.VerticalScrollBarVisibility   = ScrollBarVisibility.Auto
    dg_scroll.HorizontalScrollBarVisibility = ScrollBarVisibility.Auto
    Grid.SetRow(dg_scroll, 1)
    dg_outer.Children.Add(dg_scroll)

    status_bdr = Border()
    status_bdr.Background     = _br(243, 240, 236)
    status_bdr.BorderBrush    = _br(220, 217, 213)
    status_bdr.BorderThickness = Thickness(0, 1, 0, 0)
    status_bdr.Padding        = Thickness(16, 5, 16, 5)
    Grid.SetRow(status_bdr, 6)
    root.Children.Add(status_bdr)
    status_sp = StackPanel()
    status_sp.Orientation = Orientation.Horizontal
    status_bdr.Child = status_sp
    status_sp.Children.Add(_lbl(
        "{} fixture(s) counted".format(fixture_count),
        11, _br(40, 37, 29), FontWeights.Medium))
    if missing_count > 0:
        status_sp.Children.Add(_lbl(
            "   |   {} missing WFU param".format(missing_count),
            11, _br(218, 113, 1)))
    status_sp.Children.Add(_lbl(
        "   |   Hover chart to read values",
        11, _br(186, 185, 180)))
    status_lbl = _lbl("", 11, _br(122, 121, 116))
    status_sp.Children.Add(status_lbl)

    refs = dict(
        fvt_disp=fvt_disp, fmv_disp=fmv_disp,
        wfu_box=wfu_box,
        btn_fvt=btn_fvt, btn_fmv=btn_fmv, btn_both=btn_both,
        chart_canvas=chart_canvas, status_lbl=status_lbl,
        mat_cb=mat_cb, size_cb=size_cb, id_tb=id_tb,
        vel_result_tb=vel_result_tb, vel_dot=vel_dot,
        vel_status_tb=vel_status_tb, vel_range_tb=vel_range_tb,
        fvt_vel_tb=fvt_vel_tb, fvt_vel_dot=fvt_vel_dot, fvt_vel_sts=fvt_vel_sts,
        fmv_vel_tb=fmv_vel_tb, fmv_vel_dot=fmv_vel_dot, fmv_vel_sts=fmv_vel_sts,
        fvt_dp_tb=fvt_dp_tb, fmv_dp_tb=fmv_dp_tb, dp_cfactor_tb=dp_cfactor_tb,
    )
    return win, refs




# -- Chart drawing & event controller ------------------------------
import System.Windows.Input as WpfInput

PAD = {"left": 58, "right": 22, "top": 18, "bottom": 46}

def _dash(ln, d1=5.0, d2=3.0):
    dc = DoubleCollection()
    dc.Add(d1); dc.Add(d2)
    ln.StrokeDashArray = dc

def _line(x1, y1, x2, y2, color, thickness=1.0, dashed=False):
    ln = Line()
    ln.X1 = x1; ln.Y1 = y1
    ln.X2 = x2; ln.Y2 = y2
    ln.Stroke = SolidColorBrush(color)
    ln.StrokeThickness = thickness
    if dashed: _dash(ln)
    return ln

def _dot(cx, cy, r, fill, stroke=None, stroke_w=2.0):
    e = Ellipse()
    e.Width  = r * 2; e.Height = r * 2
    e.Fill   = SolidColorBrush(fill)
    if stroke:
        e.Stroke = SolidColorBrush(stroke)
        e.StrokeThickness = stroke_w
    Canvas.SetLeft(e, cx - r); Canvas.SetTop(e, cy - r)
    return e

def _text_lbl(text, x, y, color, size=10, weight=None):
    tb = TextBlock()
    tb.Text = text
    tb.FontSize = size
    tb.Foreground = SolidColorBrush(color)
    if weight: tb.FontWeight = weight
    Canvas.SetLeft(tb, x); Canvas.SetTop(tb, y)
    return tb

def _nice_ticks(max_val, n=5):
    """Return a list of ~n evenly-spaced, aesthetically round tick values."""
    import math
    if max_val <= 0:
        return []
    raw_step = max_val / float(n)
    mag = 10.0 ** math.floor(math.log10(raw_step))
    norm = raw_step / mag
    if   norm < 1.5: nice = 1.0
    elif norm < 3.0: nice = 2.0
    elif norm < 7.0: nice = 5.0
    else:            nice = 10.0
    step = nice * mag
    ticks = []
    v = step
    while v <= max_val * 1.01:
        ticks.append(v)
        v += step
    return ticks

def _compute_scale(wfu):
    """Return (x_max, y_max) zoomed to the relevant region around wfu."""
    if not wfu or wfu <= 0:
        return MAX_WFU, MAX_GPM
    x_max = min(max(wfu * 1.5, 60.0), MAX_WFU)
    fvt_g, _ = interp_gpm(x_max, _FVT)
    fmv_g, _ = interp_gpm(x_max, _FMV)
    vals = [g for g in [fvt_g, fmv_g] if g is not None]
    y_max = min(max(vals) * 1.15, MAX_GPM) if vals else MAX_GPM
    y_max = max(y_max, 20.0)
    return x_max, y_max

def redraw_chart(canvas, current_wfu, current_system):
    canvas.Children.Clear()
    w = canvas.ActualWidth
    h = canvas.ActualHeight
    if w < 60 or h < 60:
        return

    pl = PAD["left"]; pr = PAD["right"]
    pt = PAD["top"];  pb = PAD["bottom"]
    cw = w - pl - pr
    ch = h - pt - pb

    x_max, y_max = _compute_scale(current_wfu)

    def tx(wfu): return pl + (wfu / x_max) * cw
    def ty(gpm): return pt + ch - (gpm / y_max) * ch

    # Chart background
    bg = Rectangle()
    bg.Width = cw; bg.Height = ch
    bg.Fill = SolidColorBrush(Colors.White)
    Canvas.SetLeft(bg, pl); Canvas.SetTop(bg, pt)
    canvas.Children.Add(bg)

    grid_c  = _c(180, 178, 172, 70)
    muted_c = _c(122, 121, 116)

    # Grid lines + axis labels (dynamic ticks)
    for gpm_v in _nice_ticks(y_max, 5):
        y = ty(gpm_v)
        if pt <= y <= pt + ch:
            canvas.Children.Add(_line(pl, y, pl + cw, y, grid_c, 1, True))
            canvas.Children.Add(_text_lbl("{:.0f}".format(gpm_v), pl - 36, y - 7, muted_c))

    for wfu_v in _nice_ticks(x_max, 6):
        x = tx(wfu_v)
        if pl <= x <= pl + cw:
            canvas.Children.Add(_line(x, pt, x, pt + ch, grid_c, 1, True))
            lbl = "{:.0f}".format(wfu_v)
            canvas.Children.Add(_text_lbl(lbl, x - len(lbl) * 3, pt + ch + 6, muted_c))

    canvas.Children.Add(_text_lbl("0", pl - 14, pt + ch - 7, muted_c))

    # Axis lines
    axis_c = _c(180, 178, 172)
    canvas.Children.Add(_line(pl, pt, pl, pt + ch, axis_c, 1.5))
    canvas.Children.Add(_line(pl, pt + ch, pl + cw, pt + ch, axis_c, 1.5))

    # Axis titles
    canvas.Children.Add(_text_lbl("Fixture Units (WFU)", pl + cw / 2 - 55, pt + ch + 28, muted_c, 11))
    yt = TextBlock()
    yt.Text = "GPM"; yt.FontSize = 11
    yt.Foreground = SolidColorBrush(muted_c)
    yt.RenderTransformOrigin = Point(0.5, 0.5)
    yt.RenderTransform = RotateTransform(-90)
    Canvas.SetLeft(yt, 6); Canvas.SetTop(yt, pt + ch / 2 + 14)
    canvas.Children.Add(yt)

    # Data curves (clipped to visible range)
    show_fvt = current_system in ("fvt", "both")
    show_fmv = current_system in ("fmv", "both")

    for pairs, color, show in [
        (_FMV, C_FMV, show_fmv),
        (_FVT, C_FVT, show_fvt),
    ]:
        if not show: continue
        visible = [(wv, gv) for wv, gv in pairs if wv <= x_max * 1.01]
        if not visible: continue
        pl_obj = Polyline()
        pts = PointCollection()
        for wv, gv in visible:
            pts.Add(Point(tx(wv), ty(gv)))
        pl_obj.Points = pts
        pl_obj.Stroke = SolidColorBrush(color)
        pl_obj.StrokeThickness = 2.0
        pl_obj.StrokeLineJoin  = PenLineJoin.Round
        pl_obj.Fill = SolidColorBrush(Colors.Transparent)
        canvas.Children.Add(pl_obj)

    # Marker
    if current_wfu and 0 < current_wfu <= x_max:
        mx = tx(current_wfu)
        fvt_g, _ = interp_gpm(current_wfu, _FVT)
        fmv_g, _ = interp_gpm(current_wfu, _FMV)

        vl = _line(mx, pt, mx, pt + ch, _c(161, 44, 123, 140), 1.5, True)
        canvas.Children.Add(vl)
        wfu_tag = "{:.0f} WFU".format(current_wfu)
        canvas.Children.Add(_text_lbl(wfu_tag, mx - len(wfu_tag) * 3, pt + ch + 6,
                                      C_MARKER, 10, FontWeights.SemiBold))

        fvt_y = ty(fvt_g) if fvt_g and fvt_g <= y_max else None
        fmv_y = ty(fmv_g) if fmv_g and fmv_g <= y_max else None
        label_offset = (16 if (fvt_y and fmv_y and abs(fvt_y - fmv_y) < 20) else 0)

        for gpm_v, color, show, extra_off in [
            (fvt_g, C_FVT, show_fvt, 0),
            (fmv_g, C_FMV, show_fmv, label_offset),
        ]:
            if not (show and gpm_v is not None and gpm_v <= y_max): continue
            my = ty(gpm_v)
            canvas.Children.Add(_line(pl, my, mx, my,
                                      _c(color.R, color.G, color.B, 100), 1.5, True))
            canvas.Children.Add(_dot(mx, my, 5, color, _c(255, 255, 255)))
            canvas.Children.Add(_text_lbl("{:.1f}".format(gpm_v),
                                          pl - 38, my - 8 + extra_off,
                                          color, 10, FontWeights.SemiBold))


class LookupController(object):
    """Wires event handlers to the WPF window built by build_window()."""

    def __init__(self, window, refs, init_wfu):
        self.window  = window
        self.refs    = refs
        self.current_wfu    = init_wfu
        self.current_system = "both"

        # Apply initial button style
        self._refresh_btns()

        # Wire events
        refs["wfu_box"].TextChanged   += self._on_wfu_changed
        refs["btn_fvt"].Click         += self._on_btn
        refs["btn_fmv"].Click         += self._on_btn
        refs["btn_both"].Click        += self._on_btn
        refs["chart_canvas"].SizeChanged += self._on_resize
        refs["chart_canvas"].MouseMove   += self._on_hover
        window.Loaded                 += self._on_loaded
        refs["mat_cb"].SelectionChanged  += self._on_mat_changed
        refs["size_cb"].SelectionChanged += self._on_size_changed
        refs["id_tb"].TextChanged        += self._on_id_changed
        self._populate_sizes(PIPE_DATA[0][0])

    def _on_loaded(self, s, e):
        self._redraw()

    def _on_resize(self, s, e):
        self._redraw()

    def _on_wfu_changed(self, s, e):
        try:
            v = float(self.refs["wfu_box"].Text.strip())
            self.current_wfu = v
            self._update_kpis(v)
            self._redraw()
        except Exception:
            pass

    def _on_btn(self, s, e):
        self.current_system = s.Tag
        self._refresh_btns()
        self._redraw()

    def _refresh_btns(self):
        for b, tag in [(self.refs["btn_fvt"],  "fvt"),
                       (self.refs["btn_fmv"],  "fmv"),
                       (self.refs["btn_both"], "both")]:
            if tag == self.current_system:
                _style_btn_active(b, tag)
            else:
                _style_btn_inactive(b)

    def _update_kpis(self, wfu):
        fvt_g, _ = interp_gpm(wfu, _FVT)
        fmv_g, _ = interp_gpm(wfu, _FMV)
        self.refs["fvt_disp"].Text = "{:.1f}".format(fvt_g) if fvt_g else "--"
        self.refs["fmv_disp"].Text = "{:.1f}".format(fmv_g) if fmv_g else "--"
        self._update_velocity()

    def _redraw(self):
        redraw_chart(self.refs["chart_canvas"],
                     self.current_wfu, self.current_system)

    def _on_hover(self, s, e):
        pos = e.GetPosition(self.refs["chart_canvas"])
        w   = self.refs["chart_canvas"].ActualWidth
        h   = self.refs["chart_canvas"].ActualHeight
        cw  = w - PAD["left"] - PAD["right"]
        x   = pos.X - PAD["left"]
        if 0 <= x <= cw:
            wfu_h = (x / cw) * MAX_WFU
            fvt_g, _ = interp_gpm(wfu_h, _FVT)
            fmv_g, _ = interp_gpm(wfu_h, _FMV)
            parts = ["WFU: {:.0f}".format(wfu_h)]
            if fvt_g: parts.append("FVT: {:.1f} GPM".format(fvt_g))
            if fmv_g: parts.append("FMV: {:.1f} GPM".format(fmv_g))
            self.refs["status_lbl"].Text = "  |  ".join(parts)
        else:
            self.refs["status_lbl"].Text = "Hover over the chart to read values"



    def _populate_sizes(self, mat_name):
        cb = self.refs["size_cb"]
        cb.Items.Clear()
        entry = _pipe_entry(mat_name)
        if not entry:
            return
        for label, _id in entry[3]:
            cb.Items.Add(label)
        if cb.Items.Count > 0:
            # Default to the first size >= 3/4" or just first item
            default_idx = 0
            for k in range(cb.Items.Count):
                if cb.Items[k] == '3/4"':
                    default_idx = k
                    break
            cb.SelectedIndex = default_idx

    def _on_mat_changed(self, s, e):
        idx = s.SelectedIndex
        if idx < 0 or idx >= len(PIPE_DATA):
            return
        self._populate_sizes(PIPE_DATA[idx][0])

    def _on_size_changed(self, s, e):
        mat_idx = self.refs["mat_cb"].SelectedIndex
        size_idx = s.SelectedIndex
        if mat_idx < 0 or size_idx < 0:
            return
        entry = PIPE_DATA[mat_idx]
        if size_idx >= len(entry[3]):
            return
        _label, id_in = entry[3][size_idx]
        self.refs["id_tb"].Text = "{:.3f}".format(id_in)

    def _on_id_changed(self, s, e):
        self._update_velocity()

    def _update_velocity(self):
        refs = self.refs
        wfu = self.current_wfu
        try:
            id_in = float(refs["id_tb"].Text.strip())
        except Exception:
            id_in = 0
        mat_idx = refs["mat_cb"].SelectedIndex
        if mat_idx >= 0 and mat_idx < len(PIPE_DATA):
            entry  = PIPE_DATA[mat_idx]
            v_min  = entry[1]
            v_max  = entry[2]
        else:
            v_min, v_max = 2.0, 8.0

        def _fill_group(val_key, dot_key, sts_key, gpm, sys_tag):
            vel = calc_velocity(gpm, id_in)
            lbl, r, g, b = velocity_status(vel, v_min, v_max)
            if vel is not None:
                refs[val_key].Text       = "{:.2f}".format(vel)
                refs[val_key].Foreground = _br(r, g, b)
            else:
                refs[val_key].Text       = "--"
                refs[val_key].Foreground = _br(186, 185, 180)
            refs[dot_key].Fill            = _br(r, g, b)
            refs[sts_key].Text            = lbl if lbl != "--" else ""
            refs[sts_key].Foreground      = _br(r, g, b)

        fvt_g, _ = interp_gpm(wfu, _FVT)
        fmv_g, _ = interp_gpm(wfu, _FMV)
        _fill_group("fvt_vel_tb", "fvt_vel_dot", "fvt_vel_sts", fvt_g, "FVT")
        _fill_group("fmv_vel_tb", "fmv_vel_dot", "fmv_vel_sts", fmv_g, "FMV")

        # Range label: pipe rec. range + both GPM values
        if v_min and v_max:
            fvt_str = "{:.1f}".format(fvt_g) if fvt_g else "--"
            fmv_str = "{:.1f}".format(fmv_g) if fmv_g else "--"
            refs["vel_range_tb"].Text = (
                "rec. {:.0f}-{:.0f} ft/s   |   FVT @ {} GPM   FMV @ {} GPM".format(
                    v_min, v_max, fvt_str, fmv_str))
        else:
            refs["vel_range_tb"].Text = ""

        # Hazen-Williams pressure drop (psi/100ft)
        c_factor = entry[4] if (mat_idx >= 0 and mat_idx < len(PIPE_DATA) and len(entry) > 4) else 130
        def _fmt_dp(gpm):
            dp = calc_pressure_drop(gpm, id_in, c_factor)
            if dp is None:
                return "--", _br(186, 185, 180)
            color = _br(161, 44, 123) if dp > 6.0 else (_br(218, 113, 1) if dp > 4.0 else _br(40, 37, 29))
            return "{:.3f}".format(dp), color
        fvt_dp_txt, fvt_dp_clr = _fmt_dp(fvt_g)
        fmv_dp_txt, fmv_dp_clr = _fmt_dp(fmv_g)
        refs["fvt_dp_tb"].Text       = fvt_dp_txt
        refs["fvt_dp_tb"].Foreground = fvt_dp_clr
        refs["fmv_dp_tb"].Text       = fmv_dp_txt
        refs["fmv_dp_tb"].Foreground = fmv_dp_clr
        refs["dp_cfactor_tb"].Text   = "C = {}   (Hazen-Williams)".format(c_factor)


# -- Launch window --------------------------------------------------

win, refs = build_window(
    total_wfu, fvt_gpm, fmv_gpm,
    fixture_count, missing_count, grouped_rows
)
ctrl = LookupController(win, refs, total_wfu)
ctrl._update_kpis(total_wfu)

win.ShowDialog()   # blocks until window is closed; no temp-file needed

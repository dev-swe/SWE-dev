# -*- coding: utf-8 -*-
__title__ = 'Add Params\nto Family'
__author__ = 'EML'
__min_revit_ver__ = 2023
__max_revit_ver__ = 2026
__doc__ = """
Add Shared Parameters to Family
Reads the project shared parameter file, displays groups and parameters,
supports checkbox-based selection tray and search. Adds selected shared
parameters directly to a chosen loaded family in the project, with control
over parameter group (under which the param appears in Properties), and
whether the parameter is an instance or type parameter.
NO Threading dependencies - 100% IronPython compatible.

Author: Based on code by Evelyn Lutz
Version: 1.2
Date: April 2026
"""

# ==================== IMPORTS ====================
import clr
import os
import System

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')
clr.AddReference('System')
clr.AddReference('System.Core')

from io import open as io_open
from System.Collections.ObjectModel import ObservableCollection
from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs
from System.Windows.Threading import DispatcherTimer  # ← ADD
from System import TimeSpan                           # ← ADD (System already

from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult
from Autodesk.Revit.DB import (
    Transaction, FilteredElementCollector,
    ElementId, Family, FamilySymbol,
    ExternalDefinitionCreationOptions,
    InstanceBinding, TypeBinding,
    IFamilyLoadOptions,          # ← ADD THIS
)

# BuiltInParameterGroup removed in Revit 2023+; ForgeTypeId/GroupTypeId used instead.
try:
    from Autodesk.Revit.DB import GroupTypeId
    _USE_FORGE = True
except ImportError:
    from Autodesk.Revit.DB import BuiltInParameterGroup
    _USE_FORGE = False

from pyrevit import revit
from pyrevit.forms import WPFWindow

# ==================== SPEC TYPE MAP ====================
SPEC_TYPE_MAP = {
    'Acceleration': 'Acceleration', 'AirFlow': 'Air Flow',
    'AirFlowDensity': 'Air Flow Density',
    'AirFlowDividedByCoolingLoad': 'Air Flow Divided By Cooling Load',
    'AirFlowDividedByVolume': 'Air Flow Divided By Volume',
    'Angle': 'Angle', 'AngularSpeed': 'Angular Speed',
    'ApparentPower': 'Apparent Power', 'ApparentPowerDensity': 'Apparent Power Density',
    'Area': 'Area', 'AreaDividedByCoolingLoad': 'Area Divided By Cooling Load',
    'AreaDividedByHeatingLoad': 'Area Divided By Heating Load',
    'AreaForce': 'Area Force', 'AreaForceScale': 'Area Force Scale',
    'AreaSpringCoefficient': 'Area Spring Coefficient', 'BarDiameter': 'Bar Diameter',
    'Bool': 'Yes/No', 'Boolean': 'Yes/No', 'CableTraySize': 'Cable Tray Size',
    'ColorTemperature': 'Color Temperature', 'ConduitSize': 'Conduit Size',
    'CoolingLoad': 'Cooling Load', 'CoolingLoadDividedByArea': 'Cooling Load Divided By Area',
    'CoolingLoadDividedByVolume': 'Cooling Load Divided By Volume',
    'CostPerArea': 'Cost Per Area', 'CostRateEnergy': 'Cost Rate Energy',
    'CostRatePower': 'Cost Rate Power', 'CrackWidth': 'Crack Width',
    'CrossSection': 'Cross Section', 'Currency': 'Currency', 'Current': 'Current',
    'Custom': 'Custom', 'DecimalSheetLength': 'Decimal Sheet Length',
    'DemandFactor': 'Demand Factor', 'Diffusivity': 'Diffusivity',
    'Displacement': 'Displacement', 'Distance': 'Distance',
    'DuctInsulationThickness': 'Duct Insulation Thickness',
    'DuctLiningThickness': 'Duct Lining Thickness', 'DuctSize': 'Duct Size',
    'Efficacy': 'Efficacy', 'ElectricalFrequency': 'Frequency',
    'ElectricalPotential': 'Voltage', 'ElectricalPower': 'Power',
    'ElectricalPowerDensity': 'Power Density',
    'ElectricalResistivity': 'Electrical Resistivity',
    'ElectricalTemperature': 'Temperature',
    'ElectricalTemperatureDifference': 'Temperature Difference',
    'Energy': 'Energy', 'Factor': 'Factor', 'Flow': 'Flow',
    'FlowPerPower': 'Flow Per Power', 'Force': 'Force', 'ForceScale': 'Force Scale',
    'HeatCapacityPerArea': 'Heat Capacity Per Area', 'HeatGain': 'Heat Gain',
    'HeatTransferCoefficient': 'Heat Transfer Coefficient',
    'HeatingLoad': 'Heating Load',
    'HeatingLoadDividedByArea': 'Heating Load Divided By Area',
    'HeatingLoadDividedByVolume': 'Heating Load Divided By Volume',
    'HvacDensity': 'HVAC Density', 'HvacEnergy': 'HVAC Energy',
    'HvacFriction': 'HVAC Friction', 'HvacMassPerTime': 'HVAC Mass Per Time',
    'HvacPower': 'HVAC Power', 'HvacPowerDensity': 'HVAC Power Density',
    'HvacPressure': 'HVAC Pressure', 'HvacRoughness': 'HVAC Roughness',
    'HvacSlope': 'HVAC Slope', 'HvacTemperature': 'HVAC Temperature',
    'HvacTemperatureDifference': 'HVAC Temperature Difference',
    'HvacVelocity': 'HVAC Velocity', 'HvacViscosity': 'HVAC Viscosity',
    'Illuminance': 'Illuminance', 'Image': 'Image', 'Integer': 'Integer',
    'Int64': 'Integer',
    'IsothermalMoistureCapacity': 'Isothermal Moisture Capacity',
    'Length': 'Length', 'LineSpringCoefficient': 'Line Spring Coefficient',
    'LinearForce': 'Linear Force', 'LinearForceScale': 'Linear Force Scale',
    'LinearMoment': 'Linear Moment', 'LinearMomentScale': 'Linear Moment Scale',
    'Luminance': 'Luminance', 'LuminousFlux': 'Luminous Flux',
    'LuminousIntensity': 'Luminous Intensity', 'Mass': 'Mass',
    'MassDensity': 'Mass Density', 'MassPerUnitArea': 'Mass Per Unit Area',
    'MassPerUnitLength': 'Mass Per Unit Length', 'Material': 'Material',
    'Moment': 'Moment', 'MomentOfInertia': 'Moment Of Inertia',
    'MomentScale': 'Moment Scale', 'MultilineText': 'Multiline Text',
    'Number': 'Number', 'NumberOfPoles': 'Number of Poles', 'Period': 'Period',
    'Permeability': 'Permeability', 'PipeDimension': 'Pipe Dimension',
    'PipeInsulationThickness': 'Pipe Insulation Thickness',
    'PipeMassPerUnitLength': 'Pipe Mass Per Unit Length', 'PipeSize': 'Pipe Size',
    'PipingDensity': 'Piping Density', 'PipingFriction': 'Piping Friction',
    'PipingMass': 'Piping Mass', 'PipingMassPerTime': 'Piping Mass Per Time',
    'PipingPressure': 'Piping Pressure', 'PipingRoughness': 'Piping Roughness',
    'PipingSlope': 'Piping Slope', 'PipingTemperature': 'Piping Temperature',
    'PipingTemperatureDifference': 'Piping Temperature Difference',
    'PipingVelocity': 'Piping Velocity', 'PipingViscosity': 'Piping Viscosity',
    'PipingVolume': 'Piping Volume',
    'PointSpringCoefficient': 'Point Spring Coefficient',
    'PowerPerFlow': 'Power Per Flow', 'PowerPerLength': 'Power Per Length',
    'Pulsation': 'Pulsation', 'Reference': 'Reference',
    'ReinforcementArea': 'Reinforcement Area',
    'ReinforcementAreaPerUnitLength': 'Reinforcement Area Per Unit Length',
    'ReinforcementCover': 'Reinforcement Cover',
    'ReinforcementLength': 'Reinforcement Length',
    'ReinforcementSpacing': 'Reinforcement Spacing',
    'ReinforcementVolume': 'Reinforcement Volume',
    'Rotation': 'Rotation', 'RotationAngle': 'Rotation Angle',
    'RotationalLineSpringCoefficient': 'Rotational Line Spring Coefficient',
    'RotationalPointSpringCoefficient': 'Rotational Point Spring Coefficient',
    'SectionArea': 'Section Area', 'SectionDimension': 'Section Dimension',
    'SectionModulus': 'Section Modulus', 'SectionProperty': 'Section Property',
    'SheetLength': 'Sheet Length', 'SiteAngle': 'Site Angle', 'Slope': 'Slope',
    'SpecificHeat': 'Specific Heat',
    'SpecificHeatOfVaporization': 'Specific Heat Of Vaporization',
    'Speed': 'Speed', 'Stationing': 'Stationing',
    'StationingInterval': 'Stationing Interval', 'Stress': 'Stress',
    'String': 'Text', 'StructuralFrequency': 'Structural Frequency',
    'StructuralVelocity': 'Structural Velocity',
    'SurfaceAreaPerUnitLength': 'Surface Area Per Unit Length',
    'ThermalConductivity': 'Thermal Conductivity',
    'ThermalExpansionCoefficient': 'Thermal Expansion Coefficient',
    'ThermalGradientCoefficientForMoistureCapacity':
        'Thermal Gradient Coefficient For Moisture Capacity',
    'ThermalMass': 'Thermal Mass', 'ThermalResistance': 'Thermal Resistance',
    'Time': 'Time', 'UnitWeight': 'Unit Weight', 'Url': 'URL', 'Volume': 'Volume',
    'WarpingConstant': 'Warping Constant', 'Wattage': 'Wattage',
    'Weight': 'Weight', 'WeightPerUnitLength': 'Weight Per Unit Length',
    'WireDiameter': 'Wire Diameter', 'YesNo': 'Yes/No', 'Text': 'Text',
    'FamilyType': 'Family Type',
}

# ==================== PARAMETER GROUPS ====================
# Revit 2023+ replaced BuiltInParameterGroup with ForgeTypeId (GroupTypeId.*).
def _build_param_group_map():
    if _USE_FORGE:
        return {
            'Analysis Results':          GroupTypeId.AnalysisResults,
            'Analytical Alignment':      GroupTypeId.AnalyticalAlignment,
            'Analytical Model':          GroupTypeId.AnalyticalModel,
            'Constraints':               GroupTypeId.Constraints,
            'Construction':              GroupTypeId.Construction,
            'Data':                      GroupTypeId.Data,
            'Dimensions':                GroupTypeId.Geometry,
            'Electrical':                GroupTypeId.Electrical,
            'Electrical - Circuiting':   GroupTypeId.ElectricalCircuiting,
            'Electrical - Lighting':     GroupTypeId.ElectricalLighting,
            'Electrical - Loads':        GroupTypeId.ElectricalLoads,
            'Energy Analysis':           GroupTypeId.EnergyAnalysis,
            'Fire Protection':           GroupTypeId.FireProtection,
            'Forces':                    GroupTypeId.Forces,
            'General':                   GroupTypeId.General,
            'Graphics':                  GroupTypeId.Graphics,
            'Green Building Properties': GroupTypeId.GreenBuilding,
            'Identity Data':             GroupTypeId.IdentityData,
            'IFC Parameters':            GroupTypeId.Ifc,
            'Materials and Finishes':    GroupTypeId.Materials,
            'Mechanical':                GroupTypeId.Mechanical,
            'Mechanical - Flow':         GroupTypeId.MechanicalAirflow,
            'Mechanical - Loads':        GroupTypeId.MechanicalLoads,
            'Moments':                   GroupTypeId.Moments,
            'Other':                     GroupTypeId.General,
            'Phasing':                   GroupTypeId.Phasing,
            'Photometrics':              GroupTypeId.LightPhotometrics,
            'Plumbing':                  GroupTypeId.Plumbing,
            'Primary End':               GroupTypeId.PrimaryEnd,
            'Secondary End':             GroupTypeId.SecondaryEnd,
            'Segments and Fittings':     GroupTypeId.SegmentsFittings,
            'Structural':                GroupTypeId.Structural,
            'Structural Analysis':       GroupTypeId.StructuralAnalysis,
            'Text':                      GroupTypeId.Text,
            'Visibility':                GroupTypeId.Visibility,
        }
    else:
        return {
            'Analysis Results':          BuiltInParameterGroup.PG_ANALYSIS_RESULTS,
            'Analytical Alignment':      BuiltInParameterGroup.PG_ANALYTICAL_ALIGNMENT,
            'Analytical Model':          BuiltInParameterGroup.PG_ANALYTICAL_MODEL,
            'Constraints':               BuiltInParameterGroup.PG_CONSTRAINTS,
            'Construction':              BuiltInParameterGroup.PG_CONSTRUCTION,
            'Data':                      BuiltInParameterGroup.PG_DATA,
            'Dimensions':                BuiltInParameterGroup.PG_GEOMETRY,
            'Electrical':                BuiltInParameterGroup.PG_ELECTRICAL,
            'Electrical - Circuiting':   BuiltInParameterGroup.PG_ELECTRICAL_CIRCUITING,
            'Electrical - Lighting':     BuiltInParameterGroup.PG_ELECTRICAL_LIGHTING,
            'Electrical - Loads':        BuiltInParameterGroup.PG_ELECTRICAL_LOADS,
            'Energy Analysis':           BuiltInParameterGroup.PG_ENERGY_ANALYSIS,
            'Fire Protection':           BuiltInParameterGroup.PG_FIRE_PROTECTION,
            'Forces':                    BuiltInParameterGroup.PG_FORCES,
            'General':                   BuiltInParameterGroup.PG_GENERAL,
            'Graphics':                  BuiltInParameterGroup.PG_GRAPHICS,
            'Green Building Properties': BuiltInParameterGroup.PG_GREEN_BUILDING,
            'Identity Data':             BuiltInParameterGroup.PG_IDENTITY_DATA,
            'IFC Parameters':            BuiltInParameterGroup.PG_IFC,
            'Materials and Finishes':    BuiltInParameterGroup.PG_MATERIALS,
            'Mechanical':                BuiltInParameterGroup.PG_MECHANICAL,
            'Mechanical - Flow':         BuiltInParameterGroup.PG_MECHANICAL_AIRFLOW,
            'Mechanical - Loads':        BuiltInParameterGroup.PG_MECHANICAL_LOADS,
            'Moments':                   BuiltInParameterGroup.PG_MOMENTS,
            'Other':                     BuiltInParameterGroup.PG_INVALID,
            'Phasing':                   BuiltInParameterGroup.PG_PHASING,
            'Photometrics':              BuiltInParameterGroup.PG_LIGHT_PHOTOMETRICS,
            'Plumbing':                  BuiltInParameterGroup.PG_PLUMBING,
            'Primary End':               BuiltInParameterGroup.PG_PRIMARY_END,
            'Secondary End':             BuiltInParameterGroup.PG_SECONDARY_END,
            'Segments and Fittings':     BuiltInParameterGroup.PG_SEGMENTS_FITTINGS,
            'Structural':                BuiltInParameterGroup.PG_STRUCTURAL,
            'Structural Analysis':       BuiltInParameterGroup.PG_STRUCTURAL_ANALYSIS,
            'Text':                      BuiltInParameterGroup.PG_TEXT,
            'Visibility':                BuiltInParameterGroup.PG_VISIBILITY,
        }

PARAM_GROUP_MAP   = _build_param_group_map()
PARAM_GROUP_ORDER = sorted(PARAM_GROUP_MAP.keys())


# ==================== HELPERS ====================

def _get_doc():
    return __revit__.ActiveUIDocument.Document


def _get_app():
    return __revit__.Application


# ==================== SHARED PARAMETER FILE FUNCTIONS ====================

def read_txt_file_combined(filepath):
    """Single-pass parser for shared parameter files (UTF-16-LE)."""
    group_dict       = {}
    param_dict       = {}
    group_param_dict = {}

    try:
        with io_open(filepath, 'r', encoding='utf-16-le') as f:
            for line in f:
                fields = line.strip().split('\t', 7)
                if not fields or not fields[0]:
                    continue
                record_type = fields[0]

                if record_type == 'GROUP' and len(fields) >= 3:
                    group_dict[fields[1]] = fields[2]

                elif record_type == 'PARAM' and len(fields) >= 6:
                    param_name  = fields[2]
                    group_name  = group_dict.get(fields[5], 'Unknown')
                    description = fields[7].replace('1', '').replace('0', '') \
                                  if len(fields) > 7 else ''

                    param_dict[param_name] = {
                        'guid':        fields[1],
                        'dtype':       fields[3],
                        'dcat':        fields[4],
                        'group':       group_name,
                        'visible':     fields[6] if len(fields) > 6 else '1',
                        'description': description,
                    }
                    group_param_dict.setdefault(group_name, []).append(param_name)

    except Exception as e:
        print("Error reading shared parameter file: {0}".format(e))

    return group_dict, group_param_dict, param_dict


def get_project_shared_parameter_file(app):
    """Return the shared parameter file path from the application, or None."""
    try:
        sp_file = app.SharedParametersFilename
        return sp_file if sp_file and os.path.exists(sp_file) else None
    except Exception as ex:
        print("ERROR getting shared parameter file: {0}".format(ex))
        return None


def get_loaded_families(doc):
    """Return sorted list of (family_name, Family element, category_name)."""
    families = FilteredElementCollector(doc).OfClass(Family).ToElements()
    result = []
    for fam in families:
        try:
            if fam.IsEditable:
                cat_name = ''
                try:
                    cat_name = fam.FamilyCategory.Name if fam.FamilyCategory else ''
                except Exception:
                    pass
                result.append((fam.Name, fam, cat_name))
        except Exception:
            pass
    return sorted(result, key=lambda x: x[0].lower())


def get_existing_shared_param_guids(doc):
    """Return a set of GUID strings already bound in this project."""
    guids = set()
    it = doc.ParameterBindings.ForwardIterator()
    while it.MoveNext():
        defn = it.Key
        try:
            guid_str = str(defn.GUID).strip().lower()
            guids.add(guid_str)
        except Exception:
            pass
    return guids


# ==================== DATA CLASSES ====================

class _NotifyBase(INotifyPropertyChanged):
    """Minimal INotifyPropertyChanged mixin."""

    def __init__(self):
        self._handlers = []

    def add_PropertyChanged(self, handler):
        self._handlers.append(handler)

    def remove_PropertyChanged(self, handler):
        if handler in self._handlers:
            self._handlers.remove(handler)

    def OnPropertyChanged(self, name):
        args = PropertyChangedEventArgs(name)
        for h in self._handlers:
            h(self, args)


class SharedParameterGroupItem(_NotifyBase):
    def __init__(self, group_name):
        _NotifyBase.__init__(self)
        self._group_name = group_name

    @property
    def GroupName(self):
        return self._group_name


class SharedParameterItem(_NotifyBase):
    """Represents a shared parameter with checkbox-selection capability."""

    def __init__(self, param_name, data_type, group_name, data_cat,
                 description, guid, already_bound=False, parent_form=None):
        _NotifyBase.__init__(self)
        self._param_name    = param_name
        self._data_type     = data_type
        self._group_name    = group_name
        self._data_cat      = data_cat
        self._description   = description
        self._guid          = guid
        self._is_selected   = False
        self._already_bound = already_bound
        self._parent_form   = parent_form

    @property
    def ParamName(self):    return self._param_name
    @property
    def DataType(self):     return self._data_type
    @property
    def GroupName(self):    return self._group_name
    @property
    def DataCat(self):      return self._data_cat
    @property
    def Description(self):  return self._description
    @property
    def ParamGUID(self):    return self._guid
    @property
    def AlreadyBound(self): return self._already_bound

    @property
    def StatusLabel(self):
        return u"\u2714 Bound" if self._already_bound else ""

    @property
    def HasMeaningfulDescription(self):
        return bool(self._description and
                    self._description.strip() not in ('', '1 0', '1', '0'))

    @property
    def DisplayDescription(self):
        return self._description if self.HasMeaningfulDescription else ''

    @property
    def IsSelected(self): return self._is_selected

    @IsSelected.setter
    def IsSelected(self, value):
        if self._is_selected != value:
            self._is_selected = value
            self.OnPropertyChanged('IsSelected')
            if self._parent_form:
                try:
                    self._parent_form.on_param_selection_changed(self, value)
                except Exception as ex:
                    print("Error in selection handler: {0}".format(ex))


class FamilyItem(_NotifyBase):
    """Represents a loaded Family for display in the list."""

    def __init__(self, family_name, family_elem, category_name=''):
        _NotifyBase.__init__(self)
        self._name     = family_name
        self._family   = family_elem
        self._category = category_name

    @property
    def FamilyName(self):    return self._name
    @property
    def FamilyElem(self):    return self._family
    @property
    def CategoryName(self):  return self._category


# NEW
class FamilyParamItem(_NotifyBase):
    """Represents a shared parameter already bound to the selected family (read-only)."""

    def __init__(self, param_name, data_type, param_group, binding_type, guid=''):
        _NotifyBase.__init__(self)
        self._param_name   = param_name
        self._data_type    = data_type
        self._param_group  = param_group
        self._binding_type = binding_type
        self._guid         = guid

    @property
    def ParamName(self):    return self._param_name
    @property
    def DataType(self):     return self._data_type
    @property
    def ParamGroup(self):   return self._param_group
    @property
    def BindingType(self):  return self._binding_type
    @property
    def ParamGUID(self):    return self._guid
#


# ==================== WPF WINDOW ====================

class AddSharedParamsWindow(WPFWindow):
    """
    Add Shared Parameters to Family window.
    Layout:
        Row 0 - Title bar
        Row 1 - File path bar
        Row 2 - Search box
        Row 3 - Main two-panel area (Groups | Parameters)
        Row 4 - Horizontal splitter
        Row 5 - Bottom area:
                  Col 0: LOADED FAMILIES panel (with category filter)
                  Col 2: BINDING SETTINGS + TABBED TRAY + [Add Parameters] button
                         Tab 1: TO ADD  (parameters queued for binding)
                         Tab 2: FAMILY PARAMS  (parameters already on the family)
    """

    MAX_SELECTION = 50

    def __init__(self, app):
        xaml_path = self._write_xaml()
        WPFWindow.__init__(self, xaml_path)

        self.app = app
        self.doc = _get_doc()

        self.sp_group_dict        = {}
        self.sp_param_by_group    = {}
        self.sp_param_dict        = {}
        self.sp_unfiltered_params = None
        self._existing_guids      = set()

        self.sp_group_items     = ObservableCollection[System.Object]()
        self.sp_param_items     = ObservableCollection[System.Object]()
        self.sp_selected_items  = ObservableCollection[System.Object]()
        self.family_items       = ObservableCollection[System.Object]()
        self.family_param_items = ObservableCollection[System.Object]()  # NEW
        self._family_all        = []
        self._selected_name_set = {}

        self.sp_groups_list.ItemsSource      = self.sp_group_items
        self.sp_params_grid.ItemsSource      = self.sp_param_items
        self.sp_selected_grid.ItemsSource    = self.sp_selected_items
        self.family_list.ItemsSource         = self.family_items
        self.family_params_grid.ItemsSource  = self.family_param_items  # NEW
        self._search_timer = DispatcherTimer()
        self._search_timer.Interval = System.TimeSpan.FromMilliseconds(300)
        self._search_timer.Tick += self._on_search_timer_tick

        for grp in PARAM_GROUP_ORDER:
            self.cmb_param_group.Items.Add(grp)
        try:
            self.cmb_param_group.SelectedIndex = PARAM_GROUP_ORDER.index('Identity Data')
        except ValueError:
            self.cmb_param_group.SelectedIndex = 0

        self._load_from_project_file()
        self._populate_family_list()

    # ------------------------------------------------------------------
    # XAML
    # ------------------------------------------------------------------
    def _write_xaml(self):
        import tempfile
        xaml_path = os.path.join(tempfile.gettempdir(), 'add_shared_params_family.xaml')
        try:
            if os.path.exists(xaml_path):
                os.remove(xaml_path)
        except Exception:
            pass
        with open(xaml_path, 'w') as f:
            f.write(self._create_xaml())
        return xaml_path

    def _create_xaml(self):
        return """
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Add Shared Parameters to Family"
        Height="960" Width="1100"
        MinHeight="800" MinWidth="860"
        ShowInTaskbar="False"
        ResizeMode="CanResize"
        WindowStartupLocation="CenterScreen"
        Background="White">

    <Window.Resources>
        <SolidColorBrush x:Key="ForestBrush"     Color="#12413C"/>
        <SolidColorBrush x:Key="SandBrush"       Color="#F1E1C0"/>
        <SolidColorBrush x:Key="LightGrayBrush"  Color="#F5F5F5"/>
        <SolidColorBrush x:Key="MediumGrayBrush" Color="#E0E0E0"/>

        <Style x:Key="PrimaryFlatButton" TargetType="Button">
            <Setter Property="Background"      Value="White"/>
            <Setter Property="Foreground"      Value="{StaticResource ForestBrush}"/>
            <Setter Property="BorderBrush"     Value="{StaticResource ForestBrush}"/>
            <Setter Property="BorderThickness" Value="2"/>
            <Setter Property="Padding"         Value="15,8"/>
            <Setter Property="Margin"          Value="5"/>
            <Setter Property="FontSize"        Value="12"/>
            <Setter Property="FontWeight"      Value="Bold"/>
            <Setter Property="Height"          Value="40"/>
            <Setter Property="Cursor"          Value="Hand"/>
            <Style.Triggers>
                <Trigger Property="IsMouseOver" Value="True">
                    <Setter Property="Background" Value="{StaticResource SandBrush}"/>
                </Trigger>
                <Trigger Property="IsEnabled" Value="False">
                    <Setter Property="Opacity" Value="0.4"/>
                </Trigger>
            </Style.Triggers>
        </Style>

        <Style x:Key="AccentButton" TargetType="Button"
               BasedOn="{StaticResource PrimaryFlatButton}">
            <Setter Property="Background"  Value="{StaticResource ForestBrush}"/>
            <Setter Property="Foreground"  Value="White"/>
            <Setter Property="BorderBrush" Value="{StaticResource ForestBrush}"/>
            <Style.Triggers>
                <Trigger Property="IsMouseOver" Value="True">
                    <Setter Property="Background" Value="#0e3330"/>
                </Trigger>
                <Trigger Property="IsEnabled" Value="False">
                    <Setter Property="Opacity" Value="0.4"/>
                </Trigger>
            </Style.Triggers>
        </Style>

        <Style x:Key="SearchBox" TargetType="TextBox">
            <Setter Property="Padding"                  Value="10,8"/>
            <Setter Property="FontSize"                 Value="12"/>
            <Setter Property="BorderBrush"              Value="{StaticResource ForestBrush}"/>
            <Setter Property="BorderThickness"          Value="2"/>
            <Setter Property="VerticalContentAlignment" Value="Center"/>
        </Style>

        <Style x:Key="ColHeader" TargetType="DataGridColumnHeader">
            <Setter Property="Background"                 Value="{StaticResource SandBrush}"/>
            <Setter Property="Foreground"                 Value="{StaticResource ForestBrush}"/>
            <Setter Property="FontWeight"                 Value="Bold"/>
            <Setter Property="FontSize"                   Value="10"/>
            <Setter Property="Padding"                    Value="8,8"/>
            <Setter Property="HorizontalContentAlignment" Value="Center"/>
            <Setter Property="Height"                     Value="32"/>
        </Style>

        <Style x:Key="SettingsLabel" TargetType="TextBlock">
            <Setter Property="FontSize"          Value="12"/>
            <Setter Property="FontWeight"        Value="SemiBold"/>
            <Setter Property="Foreground"        Value="{StaticResource ForestBrush}"/>
            <Setter Property="VerticalAlignment" Value="Center"/>
            <Setter Property="Margin"            Value="0,0,8,0"/>
        </Style>

        <Style x:Key="FlatComboBox" TargetType="ComboBox">
            <Setter Property="Background"               Value="White"/>
            <Setter Property="Foreground"               Value="{StaticResource ForestBrush}"/>
            <Setter Property="BorderBrush"              Value="{StaticResource ForestBrush}"/>
            <Setter Property="BorderThickness"          Value="2"/>
            <Setter Property="Padding"                  Value="10,8"/>
            <Setter Property="FontSize"                 Value="12"/>
            <Setter Property="Height"                   Value="34"/>
            <Setter Property="VerticalContentAlignment" Value="Center"/>
            <Setter Property="Cursor"                   Value="Hand"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="ComboBox">
                        <Grid>
                            <Grid.ColumnDefinitions>
                                <ColumnDefinition Width="*"/>
                                <ColumnDefinition Width="32"/>
                            </Grid.ColumnDefinitions>
                            <Border Grid.ColumnSpan="2"
                                    Background="{TemplateBinding Background}"
                                    BorderBrush="{TemplateBinding BorderBrush}"
                                    BorderThickness="{TemplateBinding BorderThickness}"/>
                            <ContentPresenter Grid.Column="0"
                                              Content="{TemplateBinding SelectionBoxItem}"
                                              ContentTemplate="{TemplateBinding SelectionBoxItemTemplate}"
                                              Margin="10,0,0,0"
                                              VerticalAlignment="Center"
                                              IsHitTestVisible="False"/>
                            <ToggleButton Grid.Column="1"
                                          IsChecked="{Binding IsDropDownOpen,
                                                      RelativeSource={RelativeSource TemplatedParent},
                                                      Mode=TwoWay}"
                                          Background="Transparent" BorderThickness="0"
                                          Focusable="False" ClickMode="Press">
                                <Path Data="M 0 0 L 6 6 L 12 0"
                                      Stroke="{StaticResource ForestBrush}"
                                      StrokeThickness="2"
                                      HorizontalAlignment="Center"
                                      VerticalAlignment="Center"/>
                            </ToggleButton>
                            <ToggleButton Grid.Column="0"
                                          IsChecked="{Binding IsDropDownOpen,
                                                      RelativeSource={RelativeSource TemplatedParent},
                                                      Mode=TwoWay}"
                                          Background="Transparent" BorderThickness="0"
                                          Focusable="False" ClickMode="Press"/>
                            <Popup Grid.ColumnSpan="2"
                                   IsOpen="{TemplateBinding IsDropDownOpen}"
                                   AllowsTransparency="True" Focusable="False"
                                   PopupAnimation="Slide" Placement="Bottom">
                                <Border Background="White"
                                        BorderBrush="{StaticResource ForestBrush}"
                                        BorderThickness="2"
                                        MinWidth="{TemplateBinding ActualWidth}"
                                        MaxHeight="{TemplateBinding MaxDropDownHeight}">
                                    <ScrollViewer>
                                        <ItemsPresenter/>
                                    </ScrollViewer>
                                </Border>
                            </Popup>
                        </Grid>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter Property="Background" Value="{StaticResource SandBrush}"/>
                            </Trigger>
                            <Trigger Property="IsDropDownOpen" Value="True">
                                <Setter Property="Background" Value="{StaticResource SandBrush}"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
            <Style.Resources>
                <SolidColorBrush x:Key="{x:Static SystemColors.HighlightBrushKey}"     Color="#F1E1C0"/>
                <SolidColorBrush x:Key="{x:Static SystemColors.HighlightTextBrushKey}" Color="#12413C"/>
                <SolidColorBrush x:Key="{x:Static SystemColors.ControlBrushKey}"       Color="White"/>
            </Style.Resources>
        </Style>
    </Window.Resources>

    <Grid Margin="20">
        <Grid.RowDefinitions>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="Auto"/>
            <RowDefinition Height="1*"/>
            <RowDefinition Height="5"/>
            <RowDefinition Height="2*"/>
        </Grid.RowDefinitions>

        <!-- Row 0: Title -->
        <StackPanel Grid.Row="0" Orientation="Horizontal"
                    HorizontalAlignment="Center" Margin="0,0,0,10">
            <TextBlock Text="Add Shared Parameters to Family"
                       FontSize="16" FontWeight="Bold"
                       Foreground="{StaticResource ForestBrush}"/>
            <TextBlock x:Name="status_indicator"
                       FontSize="11" FontStyle="Italic"
                       Foreground="{StaticResource MediumGrayBrush}"
                       VerticalAlignment="Center" Margin="12,0,0,0"/>
        </StackPanel>

        <!-- Row 1: File path bar -->
        <Grid Grid.Row="1" Margin="0,0,0,10">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="*"/>
                <ColumnDefinition Width="Auto"/>
            </Grid.ColumnDefinitions>
            <TextBox  Grid.Column="0" x:Name="sp_file_path"
                      IsReadOnly="True" Style="{StaticResource SearchBox}"/>
            <Button   Grid.Column="1" Content="Browse..."
                      Style="{StaticResource PrimaryFlatButton}"
                      Click="browse_file_click" Width="110" Margin="5,0,0,0"/>
        </Grid>

        <!-- Row 2: Search box -->
        <TextBox Grid.Row="2" x:Name="sp_search_box"
                 Style="{StaticResource SearchBox}"
                 Text="Search shared parameters..."
                 Foreground="Gray"
                 GotFocus="sp_search_got_focus"
                 LostFocus="sp_search_lost_focus"
                 TextChanged="sp_search_changed"
                 Margin="0,0,0,10"/>

        <!-- Row 3: Main two-panel area -->
        <Grid Grid.Row="3">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="240"/>
                <ColumnDefinition Width="5"/>
                <ColumnDefinition Width="*"/>
            </Grid.ColumnDefinitions>

            <!-- LEFT: Groups -->
            <Border Grid.Column="0"
                    BorderBrush="{StaticResource ForestBrush}" BorderThickness="2">
                <Grid>
                    <Grid.RowDefinitions>
                        <RowDefinition Height="40"/>
                        <RowDefinition Height="*"/>
                    </Grid.RowDefinitions>
                    <Border Grid.Row="0" Background="{StaticResource ForestBrush}" Padding="10">
                        <TextBlock Text="PARAMETER GROUPS" Foreground="White"
                                   FontWeight="Bold" FontSize="12" VerticalAlignment="Center"/>
                    </Border>
                    <ListBox Grid.Row="1" x:Name="sp_groups_list"
                             DisplayMemberPath="GroupName"
                             SelectionChanged="sp_group_selection_changed"
                             Background="White" BorderThickness="0"
                             VirtualizingPanel.IsVirtualizing="True"
                             VirtualizingPanel.VirtualizationMode="Recycling"/>
                </Grid>
            </Border>

            <GridSplitter Grid.Column="1" Width="5"
                          Background="{StaticResource SandBrush}"
                          HorizontalAlignment="Stretch" VerticalAlignment="Stretch"/>

            <!-- RIGHT: Parameters -->
            <Border Grid.Column="2"
                    BorderBrush="{StaticResource ForestBrush}" BorderThickness="2">
                <Grid>
                    <Grid.RowDefinitions>
                        <RowDefinition Height="40"/>
                        <RowDefinition Height="*"/>
                    </Grid.RowDefinitions>
                    <Border Grid.Row="0" Background="{StaticResource ForestBrush}" Padding="10">
                        <StackPanel Orientation="Horizontal">
                            <TextBlock Text="SHARED PARAMETERS" Foreground="White"
                                       FontWeight="Bold" FontSize="12" VerticalAlignment="Center"/>
                            <TextBlock x:Name="sp_count_text" Foreground="White"
                                       FontSize="11" VerticalAlignment="Center" Margin="10,0,0,0"/>
                        </StackPanel>
                    </Border>
                    <DataGrid Grid.Row="1" x:Name="sp_params_grid"
                              AutoGenerateColumns="False"
                              CanUserAddRows="False" CanUserDeleteRows="False"
                              SelectionMode="Single"
                              GridLinesVisibility="All" HeadersVisibility="Column"
                              RowHeight="30" BorderThickness="0"
                              Background="White" RowBackground="White"
                              AlternatingRowBackground="{StaticResource LightGrayBrush}"
                              HorizontalGridLinesBrush="{StaticResource MediumGrayBrush}"
                              VerticalGridLinesBrush="{StaticResource MediumGrayBrush}"
                              VirtualizingPanel.IsVirtualizing="True"
                              VirtualizingPanel.VirtualizationMode="Recycling"
                              EnableRowVirtualization="True"
                              CanUserSortColumns="True">
                        <DataGrid.ColumnHeaderStyle>
                            <Style TargetType="DataGridColumnHeader"
                                   BasedOn="{StaticResource ColHeader}"/>
                        </DataGrid.ColumnHeaderStyle>
                        <DataGrid.Columns>
                            <DataGridCheckBoxColumn Header="SELECT"
                                Binding="{Binding IsSelected, Mode=TwoWay,
                                          UpdateSourceTrigger=PropertyChanged}"
                                Width="60"/>
                            <DataGridTextColumn Header="PARAMETER NAME"
                                               Binding="{Binding ParamName}"  Width="2.2*"
                                               IsReadOnly="True"/>
                            <DataGridTextColumn Header="DATA TYPE"
                                               Binding="{Binding DataType}"   Width="1*"
                                               IsReadOnly="True"/>
                            <DataGridTextColumn Header="GROUP"
                                               Binding="{Binding GroupName}"  Width="1.2*"
                                               IsReadOnly="True"/>
                            <DataGridTextColumn Header="STATUS"
                                               Binding="{Binding StatusLabel}" Width="80"
                                               IsReadOnly="True"/>
                            <DataGridTextColumn Header="DESCRIPTION"
                                               Binding="{Binding DisplayDescription}" Width="1.5*"
                                               IsReadOnly="True"/>
                        </DataGrid.Columns>
                    </DataGrid>
                </Grid>
            </Border>
        </Grid>

        <!-- Row 4: Splitter -->
        <GridSplitter Grid.Row="4" Height="5"
                      Background="{StaticResource SandBrush}"
                      HorizontalAlignment="Stretch" VerticalAlignment="Stretch"/>

        <!-- Row 5: Bottom area -->
        <Grid Grid.Row="5" Margin="0,8,0,0">
            <Grid.ColumnDefinitions>
                <ColumnDefinition Width="240"/>
                <ColumnDefinition Width="5"/>
                <ColumnDefinition Width="*"/>
            </Grid.ColumnDefinitions>

            <!-- LEFT: Loaded Families with category filter -->
            <Border Grid.Column="0"
                    BorderBrush="{StaticResource ForestBrush}" BorderThickness="2">
                <Grid>
                    <Grid.RowDefinitions>
                        <RowDefinition Height="40"/>
                        <RowDefinition Height="Auto"/>
                        <RowDefinition Height="*"/>
                    </Grid.RowDefinitions>
                    <Border Grid.Row="0" Background="{StaticResource ForestBrush}" Padding="10">
                        <StackPanel Orientation="Horizontal">
                            <TextBlock Text="LOADED FAMILIES" Foreground="White"
                                       FontWeight="Bold" FontSize="12" VerticalAlignment="Center"/>
                            <TextBlock x:Name="family_count_text" Foreground="White"
                                       FontSize="11" VerticalAlignment="Center" Margin="10,0,0,0"/>
                        </StackPanel>
                    </Border>
                    <ComboBox Grid.Row="1" x:Name="cmb_family_category"
                              Style="{StaticResource FlatComboBox}"
                              Margin="6,6,6,4"
                              SelectionChanged="family_category_changed"/>
                    <ListBox Grid.Row="2" x:Name="family_list"
                             DisplayMemberPath="FamilyName"
                             Background="White" BorderThickness="0"
                             Padding="0" Margin="0"
                             VirtualizingPanel.IsVirtualizing="True"
                             VirtualizingPanel.VirtualizationMode="Recycling"
                             SelectionChanged="family_selection_changed"/>
                </Grid>
            </Border>

            <GridSplitter Grid.Column="1" Width="5"
                          Background="{StaticResource SandBrush}"
                          HorizontalAlignment="Stretch" VerticalAlignment="Stretch"/>

            <!-- RIGHT: Settings + Tabbed Tray + Buttons -->
            <Grid Grid.Column="2">
                <Grid.RowDefinitions>
                    <RowDefinition Height="Auto"/>
                    <RowDefinition Height="*"/>
                    <RowDefinition Height="Auto"/>
                </Grid.RowDefinitions>

                <!-- Binding Settings -->
                <Border Grid.Row="0"
                        BorderBrush="{StaticResource ForestBrush}" BorderThickness="2"
                        Margin="0,0,0,6">
                    <Grid>
                        <Grid.RowDefinitions>
                            <RowDefinition Height="40"/>
                            <RowDefinition Height="Auto"/>
                        </Grid.RowDefinitions>
                        <Border Grid.Row="0" Background="{StaticResource ForestBrush}" Padding="10">
                            <TextBlock Text="BINDING SETTINGS" Foreground="White"
                                       FontWeight="Bold" FontSize="12" VerticalAlignment="Center"/>
                        </Border>
                        <Grid Grid.Row="1" Margin="12,10,12,10">
                            <Grid.ColumnDefinitions>
                                <ColumnDefinition Width="Auto"/>
                                <ColumnDefinition Width="*"/>
                                <ColumnDefinition Width="Auto"/>
                                <ColumnDefinition Width="Auto"/>
                                <ColumnDefinition Width="Auto"/>
                            </Grid.ColumnDefinitions>
                            <TextBlock Grid.Column="0" Text="Parameter Group:"
                                       Style="{StaticResource SettingsLabel}"/>
                            <ComboBox  Grid.Column="1" x:Name="cmb_param_group"
                                       Style="{StaticResource FlatComboBox}"
                                       MinWidth="160" Margin="0,0,20,0"/>
                            <TextBlock Grid.Column="2" Text="Binding:"
                                       Style="{StaticResource SettingsLabel}"/>
                            <RadioButton Grid.Column="3" x:Name="rb_instance"
                                         Content="Instance" IsChecked="True"
                                         Foreground="{StaticResource ForestBrush}"
                                         FontSize="12" Margin="0,0,12,0"
                                         VerticalAlignment="Center"/>
                            <RadioButton Grid.Column="4" x:Name="rb_type"
                                         Content="Type"
                                         Foreground="{StaticResource ForestBrush}"
                                         FontSize="12" VerticalAlignment="Center"/>
                        </Grid>
                    </Grid>
                </Border>

                <!-- NEW: Tabbed parameter tray -->
                <TabControl Grid.Row="1"
                            Background="White"
                            BorderBrush="{StaticResource ForestBrush}"
                            BorderThickness="2"
                            Padding="0">
                    <TabControl.Resources>
                        <Style TargetType="TabItem">
                            <Setter Property="Background"      Value="{StaticResource LightGrayBrush}"/>
                            <Setter Property="Foreground"      Value="{StaticResource ForestBrush}"/>
                            <Setter Property="BorderBrush"     Value="{StaticResource ForestBrush}"/>
                            <Setter Property="BorderThickness" Value="1"/>
                            <Setter Property="FontSize"        Value="11"/>
                            <Setter Property="FontWeight"      Value="SemiBold"/>
                            <Setter Property="Padding"         Value="12,6"/>
                            <Style.Triggers>
                                <Trigger Property="IsSelected" Value="True">
                                    <Setter Property="Background" Value="{StaticResource ForestBrush}"/>
                                    <Setter Property="Foreground" Value="White"/>
                                </Trigger>
                            </Style.Triggers>
                        </Style>
                    </TabControl.Resources>

                    <!-- Tab 1: Parameters queued to be added -->
                    <TabItem>
                        <TabItem.Header>
                            <StackPanel Orientation="Horizontal">
                                <TextBlock Text="TO ADD"/>
                                <TextBlock x:Name="selected_count_text"
                                           FontSize="10" Margin="6,0,0,0"
                                           VerticalAlignment="Center"/>
                            </StackPanel>
                        </TabItem.Header>
                        <DataGrid x:Name="sp_selected_grid"
                                  AutoGenerateColumns="False"
                                  CanUserAddRows="False" CanUserDeleteRows="False"
                                  SelectionMode="Single"
                                  GridLinesVisibility="Horizontal" HeadersVisibility="Column"
                                  RowHeight="28" BorderThickness="0"
                                  Background="White" RowBackground="White"
                                  AlternatingRowBackground="{StaticResource LightGrayBrush}"
                                  HorizontalGridLinesBrush="{StaticResource MediumGrayBrush}"
                                  CanUserSortColumns="False">
                            <DataGrid.ColumnHeaderStyle>
                                <Style TargetType="DataGridColumnHeader"
                                       BasedOn="{StaticResource ColHeader}"/>
                            </DataGrid.ColumnHeaderStyle>
                            <DataGrid.Columns>
                                <DataGridTextColumn Header="PARAMETER NAME"
                                                   Binding="{Binding ParamName}" Width="2*"
                                                   IsReadOnly="True"/>
                                <DataGridTextColumn Header="DATA TYPE"
                                                   Binding="{Binding DataType}"  Width="1*"
                                                   IsReadOnly="True"/>
                                <DataGridTextColumn Header="SP GROUP"
                                                   Binding="{Binding GroupName}" Width="1.2*"
                                                   IsReadOnly="True"/>
                                <DataGridTextColumn Header="STATUS"
                                                   Binding="{Binding StatusLabel}" Width="80"
                                                   IsReadOnly="True"/>
                            </DataGrid.Columns>
                        </DataGrid>
                    </TabItem>

                    <!-- Tab 2: Shared parameters already on the selected family -->
                    <TabItem>
                        <TabItem.Header>
                            <StackPanel Orientation="Horizontal">
                                <TextBlock Text="FAMILY PARAMS"/>
                                <TextBlock x:Name="fam_params_count_text"
                                           FontSize="10" Margin="6,0,0,0"
                                           VerticalAlignment="Center"/>
                            </StackPanel>
                        </TabItem.Header>
                        <DataGrid x:Name="family_params_grid"
                                  AutoGenerateColumns="False"
                                  CanUserAddRows="False" CanUserDeleteRows="False"
                                  SelectionMode="Single"
                                  GridLinesVisibility="Horizontal" HeadersVisibility="Column"
                                  RowHeight="28" BorderThickness="0"
                                  Background="White" RowBackground="White"
                                  AlternatingRowBackground="{StaticResource LightGrayBrush}"
                                  HorizontalGridLinesBrush="{StaticResource MediumGrayBrush}"
                                  CanUserSortColumns="True">
                            <DataGrid.ColumnHeaderStyle>
                                <Style TargetType="DataGridColumnHeader"
                                       BasedOn="{StaticResource ColHeader}"/>
                            </DataGrid.ColumnHeaderStyle>
                            <DataGrid.Columns>
                                <DataGridTextColumn Header="PARAMETER NAME"
                                                   Binding="{Binding ParamName}"   Width="2*"
                                                   IsReadOnly="True"/>
                                <DataGridTextColumn Header="DATA TYPE"
                                                   Binding="{Binding DataType}"    Width="1*"
                                                   IsReadOnly="True"/>
                                <DataGridTextColumn Header="PARAM GROUP"
                                                   Binding="{Binding ParamGroup}"  Width="1.4*"
                                                   IsReadOnly="True"/>
                                <DataGridTextColumn Header="BINDING"
                                                   Binding="{Binding BindingType}" Width="80"
                                                   IsReadOnly="True"/>
                            </DataGrid.Columns>
                        </DataGrid>
                    </TabItem>
                </TabControl>

                <!-- Action Buttons -->
                <StackPanel Grid.Row="2" Orientation="Horizontal"
                            HorizontalAlignment="Right" Margin="0,8,0,0">
                    <Button x:Name="btn_clear"
                            Content="Clear Selection"
                            Style="{StaticResource PrimaryFlatButton}"
                            Click="clear_selection_click"
                            Width="140"/>
                    <Button x:Name="btn_add_params"
                            Content="Add Parameters to Family"
                            Style="{StaticResource AccentButton}"
                            Click="add_params_click"
                            Width="220" IsEnabled="False"/>
                </StackPanel>
            </Grid>
        </Grid>
    </Grid>
</Window>
"""

    # ------------------------------------------------------------------
    # FILE LOADING
    # ------------------------------------------------------------------
    def _load_from_project_file(self):
        sp_file = get_project_shared_parameter_file(self.app)
        if sp_file:
            self.sp_file_path.Text = sp_file
            self._load_shared_params_file(sp_file)
        else:
            self.sp_file_path.Text = "No shared parameter file linked to this project."
            self.status_indicator.Text = "(Browse to a shared parameter file)"

    def _load_shared_params_file(self, filepath):
        self.sp_group_dict, self.sp_param_by_group, self.sp_param_dict = \
            read_txt_file_combined(filepath)

        self._existing_guids = get_existing_shared_param_guids(self.doc)

        self.sp_group_items.Clear()
        self.sp_group_items.Add(SharedParameterGroupItem("(All Groups)"))
        for g in sorted(self.sp_param_by_group.keys()):
            self.sp_group_items.Add(SharedParameterGroupItem(g))

        self.sp_groups_list.SelectedIndex = 0
        self.status_indicator.Text = "({0} parameters loaded)".format(
            len(self.sp_param_dict))

    # AFTER — build a set once, O(1) lookup per item
    def _build_param_items(self, names):
        selected_names = {s.ParamName for s in self.sp_selected_items}  # build once
        self.sp_param_items.Clear()
        for name in sorted(names):
            data = self.sp_param_dict.get(name, {})
            dtype = SPEC_TYPE_MAP.get(data.get('dtype', ''), data.get('dtype', ''))
            guid_str = data.get('guid', '').strip().lower()
            already = guid_str in self._existing_guids
            item = SharedParameterItem(
                param_name=name,
                data_type=dtype,
                group_name=data.get('group', ''),
                data_cat=data.get('dcat', ''),
                description=data.get('description', ''),
                guid=data.get('guid', ''),
                already_bound=already,
                parent_form=self,
            )
            if name in selected_names:  # O(1) set lookup
                item._is_selected = True
            self.sp_param_items.Add(item)
        self.sp_count_text.Text = "({0})".format(len(self.sp_param_items))

    def _populate_family_list(self):
        families = get_loaded_families(self.doc)
        self._family_all = [FamilyItem(n, f, c) for n, f, c in families]

        cats = sorted(set(fi.CategoryName for fi in self._family_all if fi.CategoryName))
        self.cmb_family_category.Items.Clear()
        self.cmb_family_category.Items.Add('(All Categories)')
        for cat in cats:
            self.cmb_family_category.Items.Add(cat)
        self.cmb_family_category.SelectedIndex = 0

        self._apply_family_filter()

    def _apply_family_filter(self):
        selected_cat = self.cmb_family_category.SelectedItem
        self.family_items.Clear()
        for fi in self._family_all:
            if not selected_cat or selected_cat == '(All Categories)' \
                    or fi.CategoryName == selected_cat:
                self.family_items.Add(fi)
        self.family_count_text.Text = '({0})'.format(len(self.family_items))

    # NEW
    def _load_family_params(self, family_elem):
        """Populate the FAMILY PARAMS tab with shared params already bound to this family."""
        self.family_param_items.Clear()
        if family_elem is None:
            self.fam_params_count_text.Text = ''
            return
        try:
            fam_cat = family_elem.FamilyCategory
            if fam_cat is None:
                self.fam_params_count_text.Text = '(no category)'
                return

            binding_map = self.doc.ParameterBindings
            it = binding_map.ForwardIterator()
            rows = []
            while it.MoveNext():
                defn    = it.Key
                binding = it.Current
                covers  = False
                try:
                    for cat in binding.Categories:
                        if cat.Id.IntegerValue == fam_cat.Id.IntegerValue:
                            covers = True
                            break
                except Exception:
                    pass
                if not covers:
                    continue

                param_name = defn.Name

                try:
                    dtype_raw = str(defn.GetDataType()).split('.')[-1]
                    dtype = SPEC_TYPE_MAP.get(dtype_raw, dtype_raw)
                except Exception:
                    dtype = ''

                try:
                    pg_raw   = str(defn.ParameterGroup)
                    pg_label = pg_raw
                    for label, val in PARAM_GROUP_MAP.items():
                        if str(val) == pg_raw:
                            pg_label = label
                            break
                except Exception:
                    pg_label = ''

                binding_type = 'Instance' \
                    if binding.GetType().Name == 'InstanceBinding' else 'Type'

                guid_str = ''
                try:
                    guid_str = str(defn.GUID).strip()
                except Exception:
                    pass

                rows.append(FamilyParamItem(
                    param_name, dtype, pg_label, binding_type, guid_str))

            rows.sort(key=lambda r: r.ParamName.lower())
            for r in rows:
                self.family_param_items.Add(r)

            n = len(self.family_param_items)
            self.fam_params_count_text.Text = '({0} param{1})'.format(
                n, 's' if n != 1 else '')

        except Exception as ex:
            self.fam_params_count_text.Text = '(error)'
            print('_load_family_params error: {0}'.format(ex))
    #

    # ------------------------------------------------------------------
    # UI EVENT HANDLERS
    # ------------------------------------------------------------------
    def browse_file_click(self, sender, args):
        from Microsoft.Win32 import OpenFileDialog
        dlg = OpenFileDialog()
        dlg.Title  = "Select Shared Parameter File"
        dlg.Filter = "Text Files (*.txt)|*.txt|All Files (*.*)|*.*"
        if dlg.ShowDialog():
            filepath = dlg.FileName
            self.sp_file_path.Text = filepath
            self.sp_selected_items.Clear()
            self._update_selected_count()
            self._load_shared_params_file(filepath)

    def sp_search_got_focus(self, sender, args):
        if self.sp_search_box.Foreground.ToString() == '#FF808080':
            self.sp_search_box.Text = ''
            self.sp_search_box.Foreground = System.Windows.Media.Brushes.Black

    def sp_search_lost_focus(self, sender, args):
        if not self.sp_search_box.Text.strip():
            self.sp_search_box.Text = 'Search shared parameters...'
            self.sp_search_box.Foreground = System.Windows.Media.Brushes.Gray

    # Replace sp_search_changed:
    def sp_search_changed(self, sender, args):
        self._search_timer.Stop()
        self._search_timer.Start()

    def _on_search_timer_tick(self, sender, args):
        self._search_timer.Stop()
        query = self.sp_search_box.Text.strip().lower()
        if not query or query == 'search shared parameters...':
            self._refresh_param_list()
            return
        matches = [n for n in self.sp_param_dict if query in n.lower()]
        self._build_param_items(matches)

    def sp_group_selection_changed(self, sender, args):
        self._refresh_param_list()

    def _refresh_param_list(self):
        sel = self.sp_groups_list.SelectedItem
        if sel is None:
            return
        group_name = sel.GroupName
        if group_name == '(All Groups)':
            names = list(self.sp_param_dict.keys())
        else:
            names = self.sp_param_by_group.get(group_name, [])
        self._build_param_items(names)

    def family_category_changed(self, sender, args):
        self._apply_family_filter()

    def family_selection_changed(self, sender, args):
        fi = self.family_list.SelectedItem
        self._load_family_params(fi.FamilyElem if fi else None)  # NEW
        self._update_add_button()


    # Replace on_param_selection_changed:
    def on_param_selection_changed(self, item, is_selected):
        if is_selected:
            if len(self._selected_name_set) >= self.MAX_SELECTION:
                item._is_selected = False
                item.OnPropertyChanged('IsSelected')
                TaskDialog.Show("Limit Reached",
                                "Maximum {0} parameters can be selected at once.".format(
                                    self.MAX_SELECTION))
                return
            if item.ParamName not in self._selected_name_set:
                self._selected_name_set[item.ParamName] = item
                self.sp_selected_items.Add(item)
        else:
            existing = self._selected_name_set.pop(item.ParamName, None)
            if existing:
                self.sp_selected_items.Remove(existing)
        self._update_selected_count()
        self._update_add_button()


    def clear_selection_click(self, sender, args):
        for item in self.sp_param_items:
            if item.IsSelected:
                item._is_selected = False
                item.OnPropertyChanged('IsSelected')
        self.sp_selected_items.Clear()
        self._selected_name_set.clear()  # ← add this
        self._update_selected_count()
        self._update_add_button()

    def _update_selected_count(self):
        n = len(self.sp_selected_items)
        self.selected_count_text.Text = "({0})".format(n)

    def _update_add_button(self):
        has_selection = len(self.sp_selected_items) > 0
        has_family    = self.family_list.SelectedItem is not None
        self.btn_add_params.IsEnabled = has_selection and has_family

    def add_params_click(self, sender, args):
        family_item = self.family_list.SelectedItem
        if family_item is None:
            TaskDialog.Show("No Family Selected",
                            "Please select a family from the Loaded Families list.")
            return

        selected = list(self.sp_selected_items)
        if not selected:
            TaskDialog.Show("No Parameters Selected",
                            "Please select at least one shared parameter.")
            return

        param_group_label = self.cmb_param_group.SelectedItem or 'Identity Data'
        bipg = PARAM_GROUP_MAP.get(param_group_label,
                                   PARAM_GROUP_MAP.get('Identity Data'))
        is_instance = bool(self.rb_instance.IsChecked)
        family = family_item.FamilyElem
        family_name = family_item.FamilyName
        binding_type_str = "Instance" if is_instance else "Type"

        msg = (
            "Add {0} parameter(s) to family '{1}' ONLY (not the whole category) "
            "as {2} parameters under group '{3}'?\n\nParameters:\n{4}"
        ).format(
            len(selected), family_name, binding_type_str, param_group_label,
            "\n".join("  - " + s.ParamName for s in selected),
        )
        result = TaskDialog.Show(
            "Confirm Add Parameters", msg,
            TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.No,
        )
        if result != TaskDialogResult.Yes:
            return

        added = []
        skipped = []
        failed = []

        #  Set shared parameter file on the app
        original_sp_file = self.app.SharedParametersFilename
        current_sp_file = self.sp_file_path.Text
        try:
            if current_sp_file and os.path.exists(current_sp_file):
                self.app.SharedParametersFilename = current_sp_file
            def_file = self.app.OpenSharedParameterFile()
        except Exception as ex:
            TaskDialog.Show("Error",
                            "Could not open shared parameter file:\n{0}".format(ex))
            return

        if def_file is None:
            TaskDialog.Show("Error", "Shared parameter file could not be opened.")
            return

        # Build GUID -> ExternalDefinition lookup
        guid_to_def = {}
        for def_group in def_file.Groups:
            for defn in def_group.Definitions:
                guid_to_def[str(defn.GUID).strip().lower()] = defn

        #  Open the family document for editing
        try:
            fam_doc = self.doc.EditFamily(family)
        except Exception as ex:
            TaskDialog.Show("Error",
                            "Could not open family '{0}' for editing:\n{1}".format(
                                family_name, ex))
            return

        if fam_doc is None:
            TaskDialog.Show("Error",
                            "EditFamily returned None for '{0}'.".format(family_name))
            return

        #  Add parameters inside the family document
        fam_mgr = fam_doc.FamilyManager

        with Transaction(fam_doc, "Add Shared Parameters to Family") as t:
            t.Start()
            try:
                # Build set of GUIDs already in this family
                existing_guids = set()
                for fp in fam_mgr.Parameters:
                    try:
                        existing_guids.add(str(fp.GUID).strip().lower())
                    except Exception:
                        pass

                for item in selected:
                    param_name = item.ParamName
                    guid_str = item.ParamGUID.strip().lower()

                    ext_def = guid_to_def.get(guid_str)
                    if ext_def is None:
                        failed.append("{0} (GUID not found in SP file)".format(param_name))
                        continue

                    if guid_str in existing_guids:
                        skipped.append(param_name)
                        continue

                    try:
                        fam_mgr.AddParameter(ext_def, bipg, is_instance)
                        added.append(param_name)
                        existing_guids.add(guid_str)
                    except Exception as ex:
                        failed.append("{0} ({1})".format(param_name, ex))

                t.Commit()
            except Exception as ex:
                t.RollBack()
                fam_doc.Close(False)
                TaskDialog.Show("Transaction Error",
                                "An error occurred inside the family document:\n{0}".format(ex))
                return

        #  Load the family back into the project
        class _OverwriteOptions(IFamilyLoadOptions):
            def OnFamilyFound(self, familyInUse, overwriteParameterValues):
                overwriteParameterValues = True
                return True

            def OnSharedFamilyFound(self, sharedFamily, familyInUse,
                                    source, overwriteParameterValues):
                overwriteParameterValues = True
                return True

        try:
            fam_doc.LoadFamily(self.doc, _OverwriteOptions())
        except Exception as ex:
            TaskDialog.Show("Warning",
                            "Parameters were added but the family could not be reloaded:\n"
                            "{0}\n\nSave and manually reload the family.".format(ex))
        finally:
            fam_doc.Close(False)

        #  Restore original SP file path
        if original_sp_file != current_sp_file:
            try:
                self.app.SharedParametersFilename = original_sp_file
            except Exception:
                pass

        #  Refresh UI
        self._existing_guids = get_existing_shared_param_guids(self.doc)
        for item in list(self.sp_param_items) + list(self.sp_selected_items):
            guid_str = item._guid.strip().lower()
            new_bound = guid_str in self._existing_guids
            if new_bound != item._already_bound:
                item._already_bound = new_bound
                item.OnPropertyChanged('StatusLabel')

        # Re-fetch the family element after reload (its ElementId may have changed)
        updated_family = None
        for f in FilteredElementCollector(self.doc).OfClass(Family).ToElements():
            if f.Name == family_name:
                updated_family = f
                break
        self._load_family_params(updated_family or family)

        #  Result summary
        lines = []
        if added:
            lines.append("ADDED ({0}):".format(len(added)))
            lines += ["  + " + n for n in added]
        if skipped:
            lines.append("\nSKIPPED - already in family ({0}):".format(len(skipped)))
            lines += ["  ~ " + n for n in skipped]
        if failed:
            lines.append("\nFAILED ({0}):".format(len(failed)))
            lines += ["  x " + n for n in failed]

        TaskDialog.Show(
            "Add Parameters Complete",
            "Family: {0}\nBinding: {1}\nGroup: {2}\n\n{3}".format(
                family_name, binding_type_str, param_group_label,
                "\n".join(lines)
            )
        )


# ==================== ENTRY POINT ====================

if __name__ == '__main__':
    app = __revit__.Application
    win = AddSharedParamsWindow(app)
    win.ShowDialog()

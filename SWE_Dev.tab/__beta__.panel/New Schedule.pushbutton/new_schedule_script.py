# -*- coding: utf-8 -*-
__title__ = 'New\nSchedule'
__author__ = 'EML'
__min_revit_ver__ = 2023
__max_revit_ver__ = 2024
__doc__ = """
Reads the project shared parameter file, displays groups and parameters,
supports checkbox-based comparison tray, search, building a new Revit Schedule
from selected parameters, and modifying an existing schedule's fields.
NO Threading dependencies - 100% IronPython compatible

Author: Based on code by Evelyn Lutz
Version: 1.8 - Refactored
Date: March 2026
"""

# ==================== IMPORTS ====================
import clr
import os
import time
import System

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('PresentationFramework')
clr.AddReference('PresentationCore')
clr.AddReference('WindowsBase')

from io import open as io_open
from System.Collections.ObjectModel import ObservableCollection
from System.ComponentModel import INotifyPropertyChanged, PropertyChangedEventArgs

from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import (
    Transaction, ViewSchedule, ScheduleFieldType,
    ElementId, BuiltInCategory, FilteredElementCollector,
    ScheduleFilter, ScheduleSortGroupField,
)

from pyrevit import revit
from pyrevit.forms import WPFWindow

# ==================== SPEC TYPE ID MAPPING ====================
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

SPEC_PROPERTIES = list(SPEC_TYPE_MAP.keys())

# ==================== DISCIPLINE / CATEGORY MAP ====================
DISCIPLINE_CATEGORY_MAP = {
    "All": None,
    "Architecture": [
        "Ceilings", "Curtain Panels", "Curtain Wall Mullions", "Doors",
        "Floors", "Generic Models", "Rooms", "Roofs", "Stairs",
        "Structural Columns", "Walls", "Windows",
    ],
    "Mechanical": [
        "Air Terminals", "Duct Accessories", "Duct Fittings", "Duct Insulations",
        "Duct Linings", "Ducts", "Flex Ducts", "Flex Pipes",
        "HVAC Zones", "Mechanical Equipment", "Pipe Accessories",
        "Pipe Fittings", "Pipe Insulations", "Pipes", "Spaces",
    ],
    "Electrical": [
        "Cable Tray Fittings", "Cable Trays", "Circuit Elements",
        "Conduit Fittings", "Conduits", "Data Devices", "Electrical Equipment",
        "Electrical Fixtures", "Fire Alarm Devices", "Lighting Devices",
        "Lighting Fixtures", "Nurse Call Devices", "Security Devices",
        "Sprinklers", "Telephone Devices",
    ],
    "Structural": [
        "Structural Beam Systems", "Structural Columns", "Structural Connections",
        "Structural Foundations", "Structural Framing", "Structural Rebar",
        "Structural Stiffeners", "Structural Trusses", "Walls",
    ],
    "Plumbing": [
        "Flex Pipes", "Pipe Accessories", "Pipe Fittings",
        "Pipe Insulations", "Pipes", "Plumbing Fixtures", "Sprinklers",
    ],
    "MEP": [
        "Air Terminals", "Duct Accessories", "Duct Fittings", "Duct Insulations",
        "Duct Linings", "Ducts", "Flex Ducts", "Flex Pipes",
        "HVAC Zones", "Mechanical Equipment", "Pipe Accessories",
        "Pipe Fittings", "Pipe Insulations", "Pipes", "Spaces",
        "Plumbing Fixtures", "Sprinklers",
        "Cable Tray Fittings", "Cable Trays", "Circuit Elements",
        "Conduit Fittings", "Conduits", "Data Devices", "Electrical Equipment",
        "Electrical Fixtures", "Fire Alarm Devices", "Lighting Devices",
        "Lighting Fixtures", "Nurse Call Devices", "Security Devices",
        "Telephone Devices",
    ],
}

DISCIPLINE_ORDER = ["MEP", "All", "Mechanical", "Electrical", "Plumbing", "Architecture", "Structural"]


# ==================== HELPERS ====================

def _get_doc():
    return __revit__.ActiveUIDocument.Document


def _is_valid_param_id(param_id):
    return param_id is not None and param_id.IntegerValue > 0


def _guid_from_param_id(param_id, doc):
    """Return lowercase GUID string for a shared parameter ElementId, or None."""
    if not _is_valid_param_id(param_id):
        return None
    try:
        ext_def = doc.GetElement(param_id)
        if ext_def is not None:
            return str(ext_def.GuidValue).strip().lower()
    except Exception:
        pass
    return None


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
    """Return the shared parameter file path for the active project, or None."""
    try:
        sp_file = app.SharedParametersFilename
        return sp_file if sp_file and os.path.exists(sp_file) else None
    except Exception as ex:
        print("ERROR getting shared parameter file: {0}".format(ex))
        return None


def get_schedulable_categories(doc=None):
    """Return {UI name: BuiltInCategory} for every schedulable category in the document."""
    if doc is None:
        doc = revit.doc

    bic_int_to_name = {
        int(bic): System.Enum.GetName(BuiltInCategory, bic)
        for bic in System.Enum.GetValues(BuiltInCategory)
    }

    sched = FilteredElementCollector(doc).OfClass(ViewSchedule).FirstElement()
    if sched is None:
        raise ValueError(
            "No ViewSchedule found in the document. "
            "At least one schedule must exist to query valid schedulable categories."
        )

    all_cats = {cat.Id.IntegerValue: cat.Name for cat in doc.Settings.Categories}

    category_map = {}
    for cat_id in sched.GetValidCategoriesForSchedule():
        int_id   = cat_id.IntegerValue
        ui_name  = all_cats.get(int_id)
        bic_name = bic_int_to_name.get(int_id)
        if ui_name and bic_name:
            category_map[ui_name] = getattr(BuiltInCategory, bic_name)

    return dict(sorted(category_map.items()))


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
                 description, guid, parent_form=None):
        _NotifyBase.__init__(self)
        self._param_name    = param_name
        self._data_type     = data_type
        self._group_name    = group_name
        self._data_cat      = data_cat
        self._description   = description
        self._guid          = guid
        self._field_heading = param_name
        self._is_selected   = False
        self._parent_form   = parent_form
        self._is_marked_for_removal = False

    @property
    def ParamName(self):   return self._param_name
    @property
    def DataType(self):    return self._data_type
    @property
    def GroupName(self):   return self._group_name
    @property
    def DataCat(self):     return self._data_cat
    @property
    def Description(self): return self._description
    @property
    def ParamGUID(self):   return self._guid

    @property
    def HasMeaningfulDescription(self):
        return bool(self._description and
                    self._description.strip() not in ('', '1 0', '1', '0'))

    @property
    def DisplayDescription(self):
        return self._description if self.HasMeaningfulDescription else ''

    @property
    def FieldHeading(self): return self._field_heading

    @FieldHeading.setter
    def FieldHeading(self, value):
        if self._field_heading != value:
            self._field_heading = value
            self.OnPropertyChanged('FieldHeading')

    @property
    def IsSelected(self): return self._is_selected

    @IsSelected.setter
    def IsSelected(self, value):
        if self._is_selected != value:
            self._is_selected = value
            self.OnPropertyChanged('IsSelected')
            if self._parent_form:
                try:
                    self._parent_form.on_shared_param_selection_changed(self, value)
                except Exception as ex:
                    print("Error in selection handler: {0}".format(ex))

    @property
    def IsMarkedForRemoval(self): return self._is_marked_for_removal

    @IsMarkedForRemoval.setter
    def IsMarkedForRemoval(self, value):
        if self._is_marked_for_removal != value:
            self._is_marked_for_removal = value
            self.OnPropertyChanged('IsMarkedForRemoval')


# ==================== WPF WINDOW ====================

class SharedParametersWindow(WPFWindow):
    """
    Standalone Shared Parameters viewer / Schedule builder.
    Layout:
        Row 0 – Title bar
        Row 1 – File path bar
        Row 2 – Search box
        Row 3 – Main two-panel area (Groups | Parameters)
        Row 4 – Horizontal splitter
        Row 5 – Bottom area:
                  Col 0: EXISTING SCHEDULES panel
                  Col 2: NEW SCHEDULE SETTINGS + SELECTED PARAMETERS tray
                         + [Modify Schedule] [Build Schedule] buttons
    """

    MAX_COMPARISON = 50
    CATEGORY_MAP   = None  # populated lazily in __init__

    def __init__(self, app):
        if SharedParametersWindow.CATEGORY_MAP is None:
            try:
                SharedParametersWindow.CATEGORY_MAP = get_schedulable_categories()
            except Exception as ex:
                print("WARNING: Could not load schedulable categories: {0}".format(ex))
                SharedParametersWindow.CATEGORY_MAP = {}

        xaml_path = self._write_xaml()
        WPFWindow.__init__(self, xaml_path)

        self.app = app

        self.sp_group_dict        = {}
        self.sp_param_by_group    = {}
        self.sp_param_dict        = {}
        self.sp_search_index      = {}
        self.sp_unfiltered_params = None
        self._guid_to_name        = {}

        self.sp_group_items      = ObservableCollection[System.Object]()
        self.sp_param_items      = ObservableCollection[System.Object]()
        self.sp_all_params       = ObservableCollection[System.Object]()
        self.sp_comparison_items = ObservableCollection[System.Object]()

        self.sp_comparison_grid.ItemsSource = self.sp_comparison_items

        for discipline in DISCIPLINE_ORDER:
            self.cmb_discipline.Items.Add(discipline)
        self.cmb_discipline.SelectedIndex = 0

        self._load_from_project_file()
        self._validate_schedule_name()
        self._populate_existing_list()

    # ------------------------------------------------------------------
    # XAML
    # ------------------------------------------------------------------
    def _write_xaml(self):
        import tempfile
        xaml_path = os.path.join(tempfile.gettempdir(), 'shared_params_standalone.xaml')
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
            Title="New Schedule"
            Height="960" Width="1100"
            MinHeight="800" MinWidth="800"
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
                <TextBlock Text="Build New Schedule"
                           FontSize="16" FontWeight="Bold"
                           Foreground="{StaticResource ForestBrush}"/>
                <TextBlock x:Name="performance_indicator"
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
                    <ColumnDefinition Width="260"/>
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
                    <ColumnDefinition Width="260"/>
                    <ColumnDefinition Width="5"/>
                    <ColumnDefinition Width="*"/>
                </Grid.ColumnDefinitions>

                <!-- LEFT: Existing Schedules -->
                <Border Grid.Column="0"
                        BorderBrush="{StaticResource ForestBrush}" BorderThickness="2">
                    <Grid>
                        <Grid.RowDefinitions>
                            <RowDefinition Height="40"/>
                            <RowDefinition Height="*"/>
                        </Grid.RowDefinitions>
                        <Border Grid.Row="0" Background="{StaticResource ForestBrush}" Padding="10">
                            <TextBlock Text="EXISTING SCHEDULES" Foreground="White"
                                       FontWeight="Bold" FontSize="12" VerticalAlignment="Center"/>
                        </Border>
                        <ListBox Grid.Row="1" x:Name="dup_schedule_list"
                                 DisplayMemberPath="Name"
                                 Background="White" BorderThickness="0"
                                 Padding="0" Margin="0"
                                 VirtualizingPanel.IsVirtualizing="True"
                                 VirtualizingPanel.VirtualizationMode="Recycling"
                                 SelectionChanged="dup_schedule_selection_changed"/>
                    </Grid>
                </Border>

                <GridSplitter Grid.Column="1" Width="5"
                              Background="{StaticResource SandBrush}"
                              HorizontalAlignment="Stretch" VerticalAlignment="Stretch"/>

                <!-- RIGHT: Settings + Tray + Buttons -->
                <Grid Grid.Column="2">
                    <Grid.RowDefinitions>
                        <RowDefinition Height="Auto"/>
                        <RowDefinition Height="*"/>
                        <RowDefinition Height="Auto"/>
                    </Grid.RowDefinitions>

                    <!-- Schedule Settings -->
                    <Border Grid.Row="0"
                            BorderBrush="{StaticResource ForestBrush}" BorderThickness="2">
                        <Grid>
                            <Grid.RowDefinitions>
                                <RowDefinition Height="40"/>
                                <RowDefinition Height="Auto"/>
                            </Grid.RowDefinitions>
                            <Border Grid.Row="0" Background="{StaticResource ForestBrush}" Padding="10">
                                <TextBlock Text="NEW SCHEDULE SETTINGS" Foreground="White"
                                           FontWeight="Bold" FontSize="12" VerticalAlignment="Center"/>
                            </Border>
                            <Grid Grid.Row="1" Margin="16,12,16,12">
                                <Grid.RowDefinitions>
                                    <RowDefinition Height="Auto"/>
                                    <RowDefinition Height="Auto"/>
                                </Grid.RowDefinitions>
                                <Grid.ColumnDefinitions>
                                    <ColumnDefinition Width="Auto"/>
                                    <ColumnDefinition Width="130"/>
                                    <ColumnDefinition Width="24"/>
                                    <ColumnDefinition Width="Auto"/>
                                    <ColumnDefinition Width="210"/>
                                    <ColumnDefinition Width="24"/>
                                    <ColumnDefinition Width="Auto"/>
                                    <ColumnDefinition Width="260"/>
                                </Grid.ColumnDefinitions>

                                <TextBlock Grid.Row="0" Grid.Column="0" Text="Discipline:"
                                           Style="{StaticResource SettingsLabel}"/>
                                <ComboBox  Grid.Row="0" Grid.Column="1" x:Name="cmb_discipline"
                                           Style="{StaticResource FlatComboBox}"
                                           SelectionChanged="discipline_changed"/>

                                <Rectangle Grid.Row="0" Grid.Column="2" Width="1"
                                           Fill="{StaticResource MediumGrayBrush}"
                                           VerticalAlignment="Stretch" Margin="12,4,12,4"/>

                                <TextBlock Grid.Row="0" Grid.Column="3" Text="Element Category:"
                                           Style="{StaticResource SettingsLabel}"/>
                                <ComboBox  Grid.Row="0" Grid.Column="4" x:Name="cmb_category"
                                           Style="{StaticResource FlatComboBox}"/>

                                <TextBlock Grid.Row="0" Grid.Column="6" Text="Schedule Name:"
                                           Style="{StaticResource SettingsLabel}"/>
                                <TextBox   Grid.Row="0" Grid.Column="7" x:Name="txt_schedule_name"
                                           Style="{StaticResource SearchBox}"
                                           Text="New Shared Parameter Schedule"
                                           VerticalContentAlignment="Center" Height="34"
                                           TextChanged="schedule_name_changed"/>

                                <TextBlock Grid.Row="1" Grid.Column="7" x:Name="lbl_name_warning"
                                           Text="A schedule with this name already exists."
                                           Foreground="#B85C00" FontSize="11" FontStyle="Italic"
                                           Margin="4,4,0,0" Visibility="Collapsed"/>
                            </Grid>
                        </Grid>
                    </Border>

                    <!-- Selected Parameters tray -->
                    <Border Grid.Row="1"
                            BorderBrush="{StaticResource ForestBrush}" BorderThickness="2"
                            Margin="0,8,0,0">
                        <Grid>
                            <Grid.RowDefinitions>
                                <RowDefinition Height="Auto"/>
                                <RowDefinition Height="*"/>
                            </Grid.RowDefinitions>
                            <Border Grid.Row="0" Background="{StaticResource ForestBrush}" Padding="8,6">
                                <Grid>
                                    <StackPanel Orientation="Horizontal">
                                        <TextBlock Text="SELECTED PARAMETERS" Foreground="White"
                                                   FontWeight="Bold" FontSize="12" VerticalAlignment="Center"/>
                                        <TextBlock x:Name="comparison_count_text" Foreground="White"
                                                   FontSize="11" VerticalAlignment="Center" Margin="10,0,0,0"/>
                                    </StackPanel>
                                    <StackPanel Orientation="Horizontal" HorizontalAlignment="Right">
                                        <Button Content="Remove Selected"
                                                Click="remove_selected_comparison_click"
                                                Background="{StaticResource SandBrush}"
                                                Foreground="{StaticResource ForestBrush}"
                                                BorderThickness="0" Padding="10,5"
                                                FontWeight="Bold" Cursor="Hand" Margin="0,0,6,0"/>
                                        <Button Content="Clear All"
                                                Click="clear_comparison_click"
                                                Background="{StaticResource SandBrush}"
                                                Foreground="{StaticResource ForestBrush}"
                                                BorderThickness="0" Padding="10,5"
                                                FontWeight="Bold" Cursor="Hand"/>
                                    </StackPanel>
                                </Grid>
                            </Border>
                            <DataGrid Grid.Row="1" x:Name="sp_comparison_grid"
                                      AutoGenerateColumns="False"
                                      CanUserAddRows="False" CanUserDeleteRows="False"
                                      IsReadOnly="False" SelectionMode="Single"
                                      GridLinesVisibility="All" HeadersVisibility="Column"
                                      RowHeight="30" BorderThickness="0"
                                      Background="White" RowBackground="White"
                                      AlternatingRowBackground="{StaticResource LightGrayBrush}"
                                      HorizontalGridLinesBrush="{StaticResource MediumGrayBrush}"
                                      VerticalGridLinesBrush="{StaticResource MediumGrayBrush}"
                                      VirtualizingPanel.IsVirtualizing="True"
                                      VirtualizingPanel.VirtualizationMode="Recycling"
                                      EnableRowVirtualization="True">
                                <DataGrid.ColumnHeaderStyle>
                                    <Style TargetType="DataGridColumnHeader"
                                           BasedOn="{StaticResource ColHeader}"/>
                                </DataGrid.ColumnHeaderStyle>
                                <DataGrid.Columns>
                                    <DataGridCheckBoxColumn Header="SELECT"
                                        Binding="{Binding IsMarkedForRemoval, Mode=TwoWay,
                                                  UpdateSourceTrigger=PropertyChanged}"
                                        Width="64"/>
                                    <DataGridTextColumn Header="FIELD HEADING"
                                                       Binding="{Binding FieldHeading, Mode=TwoWay,
                                                                 UpdateSourceTrigger=PropertyChanged}"
                                                       Width="1.8*" IsReadOnly="False"/>
                                    <DataGridTextColumn Header="PARAMETER NAME"
                                                       Binding="{Binding ParamName}"    Width="2*"
                                                       IsReadOnly="True"/>
                                    <DataGridTextColumn Header="DATA TYPE"
                                                       Binding="{Binding DataType}"     Width="1*"
                                                       IsReadOnly="True"/>
                                    <DataGridTextColumn Header="GROUP"
                                                       Binding="{Binding GroupName}"    Width="1.2*"
                                                       IsReadOnly="True"/>
                                </DataGrid.Columns>
                            </DataGrid>
                        </Grid>
                    </Border>

                    <!-- Bottom buttons -->
                    <StackPanel Grid.Row="2" Orientation="Horizontal"
                                HorizontalAlignment="Center" Margin="0,10,0,0">
                        <Button x:Name="modify_schedule_button"
                                Content="Modify Schedule"
                                Style="{StaticResource PrimaryFlatButton}"
                                Click="modify_schedule_click"
                                IsEnabled="False"
                                Width="200"/>
                        <Button x:Name="build_schedule_button"
                                Content="Build Schedule"
                                Style="{StaticResource PrimaryFlatButton}"
                                Click="build_schedule_click"
                                Width="200"/>
                    </StackPanel>
                </Grid>
            </Grid>
        </Grid>
    </Window>
    """

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------
    def _make_param_item(self, param_name, info, parent_form=None):
        """Build a SharedParameterItem from a param_dict info block."""
        return SharedParameterItem(
            str(param_name),
            str(info.get('dtype', '')),
            str(info.get('group', '')),
            str(info.get('dcat', '')),
            str(info.get('description', '')),
            str(info.get('guid', '')),
            parent_form,
        )

    def _build_guid_to_sf(self, sched_def, doc):
        """Return {guid_str: SchedulableField} for all shared param schedulable fields."""
        guid_to_sf = {}
        for sf in sched_def.GetSchedulableFields():
            guid = _guid_from_param_id(sf.ParameterId, doc)
            if guid:
                guid_to_sf[guid] = sf
        return guid_to_sf

    def _reset_search_box(self):
        self.sp_search_box.Text       = "Search shared parameters..."
        self.sp_search_box.Foreground = System.Windows.Media.Brushes.Gray

    # ------------------------------------------------------------------
    # Schedule snapshot / restore
    # ------------------------------------------------------------------
    @staticmethod
    def _try_get(obj, attr, default=None):
        try:
            return getattr(obj, attr)
        except Exception:
            return default

    def _field_key(self, field, doc):
        """Return a stable identity key for a schedule field."""
        guid = _guid_from_param_id(field.ParameterId, doc)
        if guid:
            return ('guid', guid)
        if _is_valid_param_id(field.ParameterId):
            return ('param_id', field.ParameterId.IntegerValue)
        return ('name', field.GetName())

    def _snapshot_schedule_settings(self, sched_def, doc):
        snap = {'filters': [], 'sort_groups': [], 'field_snapshots': {}}
        try:
            snap['filters'] = list(sched_def.GetFilters())
        except Exception as ex:
            print("_snapshot: GetFilters error: {0}".format(ex))
        try:
            snap['sort_groups'] = list(sched_def.GetSortGroupFields())
        except Exception as ex:
            print("_snapshot: GetSortGroupFields error: {0}".format(ex))

        _tg = self._try_get
        try:
            for i in range(sched_def.GetFieldCount()):
                field = sched_def.GetField(i)
                key   = self._field_key(field, doc)
                snap['field_snapshots'][key] = {
                    'ColumnHeading':           _tg(field, 'ColumnHeading'),
                    'IsHidden':                _tg(field, 'IsHidden', False),
                    'HorizontalAlignment':     _tg(field, 'HorizontalAlignment'),
                    'HeadingOrientation':      _tg(field, 'HeadingOrientation'),
                    'GridColumnWidth':         _tg(field, 'GridColumnWidth'),
                    'SheetColumnWidth':        _tg(field, 'SheetColumnWidth'),
                    'DisplayType':             _tg(field, 'DisplayType'),
                    'FormatOptions':           self.__get_fmt(field),
                    'Style':                   self.__get_style(field),
                    'DisplayTotals':           _tg(field, 'DisplayTotals'),
                    'TotalByAssemblyType':     _tg(field, 'TotalByAssemblyType'),
                    'MultipleValuesDisplayType': _tg(field, 'MultipleValuesDisplayType'),
                    'MultipleValuesCustomText':  _tg(field, 'MultipleValuesCustomText'),
                }
        except Exception as ex:
            print("_snapshot: field loop error: {0}".format(ex))
        return snap

    @staticmethod
    def __get_fmt(field):
        try:   return field.GetFormatOptions()
        except Exception: return None

    @staticmethod
    def __get_style(field):
        try:   return field.GetStyle()
        except Exception: return None

    def _restore_field_settings(self, new_field, data):
        _tg = self._try_get
        for attr in ('ColumnHeading', 'IsHidden', 'HorizontalAlignment',
                     'HeadingOrientation', 'GridColumnWidth', 'SheetColumnWidth',
                     'DisplayType', 'DisplayTotals', 'TotalByAssemblyType',
                     'MultipleValuesDisplayType', 'MultipleValuesCustomText'):
            if data.get(attr) is not None:
                try:
                    setattr(new_field, attr, data[attr])
                except Exception:
                    pass
        fmt = data.get('FormatOptions')
        if fmt is not None:
            try: new_field.SetFormatOptions(fmt)
            except Exception: pass
        style = data.get('Style')
        if style is not None:
            try: new_field.SetStyle(style)
            except Exception: pass

    # ------------------------------------------------------------------
    # Modify Schedule
    # ------------------------------------------------------------------
    def modify_schedule_click(self, sender, e):
        try:
            target = self.dup_schedule_list.SelectedItem
            if target is None:
                TaskDialog.Show("No Selection",
                                "Please select a schedule from the Existing Schedules list.")
                return

            if self.sp_comparison_items.Count == 0:
                TaskDialog.Show("No Parameters",
                                "The Selected Parameters tray is empty.\n"
                                "Add parameters before modifying a schedule.")
                return

            new_name   = self.txt_schedule_name.Text.strip() or target.Name
            tray_items = list(self.sp_comparison_items)
            doc        = _get_doc()

            restored_filters = restored_sg = unrestorable_filters = 0

            with Transaction(doc, "Modify Schedule: {0}".format(new_name)) as t:
                t.Start()
                sched_def = target.Definition

                # Step 1: Snapshot before touching fields
                snap = self._snapshot_schedule_settings(sched_def, doc)

                # Build old FieldId → key map for filter/sort remapping
                old_fid_to_key = {
                    sched_def.GetField(i).FieldId: self._field_key(sched_def.GetField(i), doc)
                    for i in range(sched_def.GetFieldCount())
                }

                # Step 2: Remove all existing fields
                for idx in range(sched_def.GetFieldCount() - 1, -1, -1):
                    try:
                        sched_def.RemoveField(sched_def.GetField(idx).FieldId)
                    except Exception:
                        pass

                # Step 3: Build GUID → SchedulableField map
                guid_to_sf = self._build_guid_to_sf(sched_def, doc)

                # Step 4: Re-add fields from tray
                added_fields        = []
                skipped_fields      = []
                key_to_new_fid      = {}

                for tray_item in tray_items:
                    guid_key = str(tray_item.ParamGUID).strip().lower()
                    sf = guid_to_sf.get(guid_key)
                    if sf is None:
                        skipped_fields.append(tray_item.ParamName)
                        continue
                    try:
                        new_field  = sched_def.AddField(sf)
                        new_key    = ('guid', guid_key)
                        field_data = snap['field_snapshots'].get(new_key)
                        if field_data:
                            heading = (tray_item.FieldHeading or '').strip()
                            if heading:
                                field_data = dict(field_data)
                                field_data['ColumnHeading'] = heading
                            self._restore_field_settings(new_field, field_data)
                        else:
                            new_field.ColumnHeading = (
                                tray_item.FieldHeading or tray_item.ParamName
                            ).strip() or tray_item.ParamName
                        key_to_new_fid[new_key] = new_field.FieldId
                        added_fields.append(
                            u"{0}  \u2192  \"{1}\"".format(
                                tray_item.ParamName, new_field.ColumnHeading)
                        )
                    except Exception as ex:
                        skipped_fields.append("{0} ({1})".format(tray_item.ParamName, ex))

                # Step 5: Restore Filters
                try:
                    sched_def.ClearFilters()
                    for f in snap['filters']:
                        old_key = old_fid_to_key.get(f.FieldId)
                        new_fid = key_to_new_fid.get(old_key) if old_key else None
                        if new_fid is None:
                            unrestorable_filters += 1
                            continue
                        # Try value getters in priority order
                        new_filter = None
                        for getter in ('GetStringValue', 'GetElementIdValue',
                                       'GetDoubleValue', 'GetIntegerValue'):
                            try:
                                val = getattr(f, getter)()
                                new_filter = ScheduleFilter(new_fid, f.FilterType, val)
                                break
                            except Exception:
                                pass
                        if new_filter:
                            try:
                                sched_def.AddFilter(new_filter)
                                restored_filters += 1
                            except Exception as fex:
                                print("Filter restore error: {0}".format(fex))
                                unrestorable_filters += 1
                        else:
                            unrestorable_filters += 1
                except Exception as ex:
                    print("Restore filters error: {0}".format(ex))

                # Step 6: Restore Sort/Group fields
                try:
                    sched_def.ClearSortGroupFields()
                    for sgf in snap['sort_groups']:
                        old_key = old_fid_to_key.get(sgf.FieldId)
                        new_fid = key_to_new_fid.get(old_key) if old_key else None
                        if new_fid is None:
                            continue
                        try:
                            new_sgf = ScheduleSortGroupField(new_fid)
                            new_sgf.SortOrder     = sgf.SortOrder
                            new_sgf.ShowHeader    = sgf.ShowHeader
                            new_sgf.ShowFooter    = sgf.ShowFooter
                            new_sgf.ShowBlankLine = sgf.ShowBlankLine
                            sched_def.AddSortGroupField(new_sgf)
                            restored_sg += 1
                        except Exception as sgex:
                            print("Sort/Group restore error: {0}".format(sgex))
                except Exception as ex:
                    print("Restore sort/group error: {0}".format(ex))

                # Step 7: Rename
                if target.Name != new_name:
                    try:
                        target.Name = new_name
                    except Exception as rex:
                        print("Rename error: {0}".format(rex))

                t.Commit()

            self._populate_existing_list()
            try:
                __revit__.ActiveUIDocument.RequestViewChange(target)
            except Exception:
                pass

            lines = [
                u"\u2705 '{0}' modified successfully.".format(new_name),
                u"   Filters restored: {0}  |  Sort/Group restored: {1}".format(
                    restored_filters, restored_sg),
                "",
                "Fields set ({0}):".format(len(added_fields)),
            ] + [u"  \u2022 " + x for x in added_fields]

            if skipped_fields:
                lines += [
                    "",
                    u"\u26a0 Not schedulable for this category ({0}):".format(len(skipped_fields)),
                ] + [u"  \u2022 " + n for n in skipped_fields]

            if unrestorable_filters:
                lines += [
                    "",
                    u"\u26a0 {0} filter(s) could not be restored.".format(unrestorable_filters),
                ]

            TaskDialog.Show("Modify Schedule Complete", "\n".join(lines))

        except Exception as ex:
            import traceback
            TaskDialog.Show(
                "Modify Schedule Error",
                "An error occurred:\n{0}\n\n{1}".format(ex, traceback.format_exc())
            )

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def _load_from_project_file(self):
        sp_file = get_project_shared_parameter_file(self.app)
        if sp_file:
            self._load_file(sp_file)
        else:
            self.sp_file_path.Text = u"\u26a0 No shared parameter file configured for this project"
            self.Title = "Shared Parameters Viewer"

    def _load_file(self, sp_file):
        try:
            start = time.time()
            self.Title = "Shared Parameters Viewer - Loading..."

            for d in (self.sp_group_dict, self.sp_param_by_group,
                      self.sp_param_dict, self.sp_search_index, self._guid_to_name):
                d.clear()
            for col in (self.sp_all_params, self.sp_group_items, self.sp_param_items):
                col.Clear()
            self.sp_unfiltered_params = None

            self.sp_group_dict, self.sp_param_by_group, self.sp_param_dict = \
                read_txt_file_combined(sp_file)

            if not self.sp_param_dict:
                self.sp_file_path.Text = \
                    u"\u26a0 No parameters found - verify this is a valid shared parameter file"
                self.Title = "Shared Parameters Viewer"
                return

            for param_name, info in self.sp_param_dict.items():
                item = self._make_param_item(param_name, info, self)
                self.sp_all_params.Add(item)
                self.sp_search_index[param_name.lower()] = item
                guid_key = str(info.get('guid', '')).strip().lower()
                if guid_key:
                    self._guid_to_name[guid_key] = param_name

            for _gid, gname in sorted(self.sp_group_dict.items(), key=lambda x: x[1]):
                self.sp_group_items.Add(SharedParameterGroupItem(gname))

            self.sp_groups_list.ItemsSource = self.sp_group_items

            total_params = len(self.sp_param_dict)
            total_groups = len(self.sp_group_dict)

            self.sp_file_path.Text  = sp_file
            self.sp_count_text.Text = "({0} parameters)".format(total_params)
            self.update_comparison_count()
            self.performance_indicator.Text = \
                u"\u26a1 Loaded {0} params / {1} groups in {2:.2f}s".format(
                    total_params, total_groups, time.time() - start)
            self.Title = "Shared Parameters Viewer ({0} parameters)".format(total_params)
            self._reset_search_box()

        except Exception as ex:
            TaskDialog.Show("Error", "Failed to load shared parameter file:\n{0}".format(ex))
            self.sp_file_path.Text = "Error loading shared parameter file"

    # ------------------------------------------------------------------
    # Existing Schedules panel
    # ------------------------------------------------------------------
    def _populate_existing_list(self):
        try:
            schedules = sorted(
                FilteredElementCollector(_get_doc()).OfClass(ViewSchedule).ToElements(),
                key=lambda s: s.Name,
            )
            self.dup_schedule_list.Items.Clear()
            for sched in schedules:
                self.dup_schedule_list.Items.Add(sched)
        except Exception as ex:
            print("_populate_existing_list error: {0}".format(ex))

    def _update_action_buttons(self):
        has_selection = self.dup_schedule_list.SelectedItem is not None
        has_params    = self.sp_comparison_items.Count > 0
        self.modify_schedule_button.IsEnabled = has_selection and has_params

    def dup_schedule_selection_changed(self, sender, e):
        try:
            selected = self.dup_schedule_list.SelectedItem
            if selected is None:
                self._update_action_buttons()
                return

            self.txt_schedule_name.Text = selected.Name
            self.sp_comparison_items.Clear()

            doc     = _get_doc()
            src_def = selected.Definition
            skipped = 0

            for i in range(src_def.GetFieldCount()):
                src_field = src_def.GetField(i)
                guid_key  = _guid_from_param_id(src_field.ParameterId, doc)

                if not guid_key:
                    skipped += 1
                    continue

                param_name = self._guid_to_name.get(guid_key)
                if param_name and param_name in self.sp_param_dict:
                    comp = self._make_param_item(param_name, self.sp_param_dict[param_name])
                else:
                    name = (src_field.GetName() if hasattr(src_field, 'GetName')
                            else str(src_field.ColumnHeading))
                    comp = SharedParameterItem(str(name), '', '', '', '', str(guid_key))

                comp._field_heading = str(src_field.ColumnHeading)
                comp._is_selected   = True
                self.sp_comparison_items.Add(comp)

            self.update_comparison_count()
            self._update_action_buttons()

            if skipped:
                print("dup_schedule_selection_changed: {0} non-shared-param field(s) skipped."
                      .format(skipped))

        except Exception as ex:
            import traceback
            print("dup_schedule_selection_changed error: {0}\n{1}"
                  .format(ex, traceback.format_exc()))

    # ------------------------------------------------------------------
    # Group selection
    # ------------------------------------------------------------------
    def sp_group_selection_changed(self, sender, e):
        try:
            selected = self.sp_groups_list.SelectedItem
            if not selected:
                return

            tray_guids = {c.ParamGUID for c in self.sp_comparison_items}

            self.sp_param_items.Clear()
            for param_name in self.sp_param_by_group.get(selected.GroupName, []):
                info = self.sp_param_dict.get(param_name)
                if info is None:
                    continue
                item = self._make_param_item(param_name, info, self)
                item._is_selected = str(info.get('guid', '')) in tray_guids
                self.sp_param_items.Add(item)

            self.sp_unfiltered_params       = self.sp_param_items
            self.sp_params_grid.ItemsSource = self.sp_param_items
            self._reset_search_box()

        except Exception as ex:
            print("Error in group selection: {0}".format(ex))

    # ------------------------------------------------------------------
    # Checkbox selection → comparison tray
    # ------------------------------------------------------------------
    def on_shared_param_selection_changed(self, item, is_selected):
        try:
            if is_selected:
                if self.sp_comparison_items.Count >= self.MAX_COMPARISON:
                    TaskDialog.Show(
                        "Limit Reached",
                        "Maximum {0} parameters can be compared at once.\n"
                        "Please clear some selections first.".format(self.MAX_COMPARISON)
                    )
                    item._is_selected = False
                    return

                if not any(c.ParamGUID == item.ParamGUID for c in self.sp_comparison_items):
                    comp = SharedParameterItem(
                        item.ParamName, item.DataType, item.GroupName,
                        item.DataCat, item.Description, item.ParamGUID, None
                    )
                    comp._is_selected = True
                    self.sp_comparison_items.Add(comp)
            else:
                to_remove = next(
                    (c for c in self.sp_comparison_items if c.ParamGUID == item.ParamGUID), None
                )
                if to_remove:
                    self.sp_comparison_items.Remove(to_remove)

            self.update_comparison_count()
            self._update_action_buttons()

        except Exception as ex:
            print("Error in selection handler: {0}".format(ex))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def sp_search_got_focus(self, sender, e):
        if self.sp_search_box.Text == "Search shared parameters...":
            self.sp_search_box.Text       = ""
            self.sp_search_box.Foreground = System.Windows.Media.Brushes.Black

    def sp_search_lost_focus(self, sender, e):
        if not self.sp_search_box.Text:
            self._reset_search_box()

    def sp_search_changed(self, sender, e):
        if self.sp_search_box.Text == "Search shared parameters...":
            return
        try:
            search_text = self.sp_search_box.Text.strip()
            if not search_text:
                if self.sp_unfiltered_params is not None:
                    self.sp_params_grid.ItemsSource = self.sp_unfiltered_params
                return

            tray_guids   = {c.ParamGUID for c in self.sp_comparison_items}
            search_lower = search_text.lower()
            filtered     = ObservableCollection[System.Object]()

            for name_lower, item in self.sp_search_index.items():
                if search_lower in name_lower:
                    new_item = SharedParameterItem(
                        item.ParamName, item.DataType, item.GroupName,
                        item.DataCat, item.Description, item.ParamGUID, self
                    )
                    new_item._is_selected = item.ParamGUID in tray_guids
                    filtered.Add(new_item)

            self.sp_params_grid.ItemsSource = filtered

        except Exception as ex:
            print("Search error: {0}".format(ex))

    # ------------------------------------------------------------------
    # Schedule name validation
    # ------------------------------------------------------------------
    def _validate_schedule_name(self):
        try:
            name = self.txt_schedule_name.Text.strip()
            if not name:
                self.lbl_name_warning.Visibility = System.Windows.Visibility.Collapsed
                return
            existing = {
                v.Name for v in FilteredElementCollector(_get_doc())
                .OfClass(ViewSchedule).ToElements()
            }
            self.lbl_name_warning.Visibility = (
                System.Windows.Visibility.Visible
                if name in existing
                else System.Windows.Visibility.Collapsed
            )
        except Exception as ex:
            print("_validate_schedule_name error: {0}".format(ex))

    def schedule_name_changed(self, sender, e):
        self._validate_schedule_name()

    # ------------------------------------------------------------------
    # Discipline / category filter
    # ------------------------------------------------------------------
    def discipline_changed(self, sender, e):
        try:
            discipline = self.cmb_discipline.SelectedItem
            if discipline is None:
                return
            allowed = DISCIPLINE_CATEGORY_MAP.get(discipline)
            self.cmb_category.Items.Clear()
            for cat_name in sorted(self.CATEGORY_MAP.keys()):
                if allowed is None or cat_name in allowed:
                    self.cmb_category.Items.Add(cat_name)
            if self.cmb_category.Items.Count > 0:
                self.cmb_category.SelectedIndex = 0
        except Exception as ex:
            print("discipline_changed error: {0}".format(ex))

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def browse_file_click(self, sender, e):
        try:
            from System.Windows.Forms import OpenFileDialog, DialogResult
            dlg = OpenFileDialog()
            dlg.Filter          = "Shared Parameter Files (*.txt)|*.txt|All Files (*.*)|*.*"
            dlg.DefaultExt      = "txt"
            dlg.Title           = "Select Shared Parameter File"
            dlg.CheckFileExists = True

            current = self.sp_file_path.Text
            if current and os.path.exists(current):
                dlg.InitialDirectory = os.path.dirname(current)
                dlg.FileName         = os.path.basename(current)

            if dlg.ShowDialog() == DialogResult.OK:
                self._load_file(dlg.FileName)
        except Exception as ex:
            TaskDialog.Show("Error", "File dialog failed: {0}".format(ex))

    def clear_comparison_click(self, sender, e):
        try:
            self.sp_comparison_items.Clear()
            source = self.sp_params_grid.ItemsSource
            if source:
                for item in source:
                    item._is_selected = False
                self.sp_params_grid.ItemsSource = None
                self.sp_params_grid.ItemsSource = source
            self.update_comparison_count()
            self._update_action_buttons()
        except Exception as ex:
            print("Error clearing comparison: {0}".format(ex))

    def remove_selected_comparison_click(self, sender, e):
        try:
            to_remove = [item for item in self.sp_comparison_items if item.IsMarkedForRemoval]
            for item in to_remove:
                self.sp_comparison_items.Remove(item)
                item.IsSelected         = False
                item.IsMarkedForRemoval = False
            self.update_comparison_count()
            self._update_action_buttons()
        except Exception as ex:
            print("remove_selected_comparison_click error: {0}".format(ex))

    def build_schedule_click(self, sender, e):
        try:
            if self.sp_comparison_items.Count == 0:
                TaskDialog.Show(
                    "No Parameters Selected",
                    "Please check at least one parameter in the grid before building a schedule."
                )
                return

            schedule_name   = self.txt_schedule_name.Text.strip() or "New Shared Parameter Schedule"
            chosen_cat_name = str(self.cmb_category.SelectedItem)
            category_id     = ElementId(self.CATEGORY_MAP[chosen_cat_name])
            doc             = _get_doc()

            if doc is None:
                TaskDialog.Show("Error", "No active Revit document found.")
                return

            tray_order     = list(self.sp_comparison_items)
            added_fields   = []
            skipped_fields = []
            schedule       = None

            with Transaction(doc, "Build Schedule: {0}".format(schedule_name)) as t:
                t.Start()
                schedule  = ViewSchedule.CreateSchedule(doc, category_id)
                schedule.Name = schedule_name
                sched_def = schedule.Definition

                guid_to_sf = {}
                for sf in sched_def.GetSchedulableFields():
                    if sf.FieldType not in (ScheduleFieldType.Instance,
                                            ScheduleFieldType.ElementType):
                        continue
                    guid = _guid_from_param_id(sf.ParameterId, doc)
                    if guid:
                        guid_to_sf[guid] = sf

                for tray_item in tray_order:
                    guid_key = str(tray_item.ParamGUID).strip().lower()
                    sf = guid_to_sf.get(guid_key)
                    if sf is None:
                        skipped_fields.append(tray_item.ParamName)
                        continue
                    new_field = sched_def.AddField(sf)
                    new_field.ColumnHeading = (
                        tray_item.FieldHeading or tray_item.ParamName
                    ).strip() or tray_item.ParamName
                    added_fields.append(
                        u"{0}  \u2192  \"{1}\"".format(tray_item.ParamName, new_field.ColumnHeading)
                    )

                t.Commit()

            self._populate_existing_list()
            try:
                __revit__.ActiveUIDocument.RequestViewChange(schedule)
            except Exception as ex:
                print("Could not open schedule view: {0}".format(ex))

            self.Close()

        except Exception as ex:
            import traceback
            TaskDialog.Show(
                "Build Schedule Error",
                "An error occurred:\n{0}\n\n{1}".format(ex, traceback.format_exc())
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def update_comparison_count(self):
        count = self.sp_comparison_items.Count
        self.comparison_count_text.Text = (
            "({0}/{1} MAX)".format(count, self.MAX_COMPARISON)
            if count >= self.MAX_COMPARISON
            else "({0} selected)".format(count)
        )


# ==================== MAIN EXECUTION ====================

def main():
    try:
        window = SharedParametersWindow(__revit__.Application)
        window.ShowDialog()
    except Exception as e:
        TaskDialog.Show("Error", "An error occurred: {0}".format(e))
        import traceback
        print(traceback.format_exc())


if __name__ == '__main__':
    main()

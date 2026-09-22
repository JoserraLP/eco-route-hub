"""
Constants and unit conversion factors for EPA database parser scripts.
"""

# Default vehicle physical parameters
DEFAULT_VEHICLE_RF: float = 0.015
DEFAULT_VEHICLE_CX: float = 0.30
DEFAULT_VEHICLE_B: float = 0.0

# Fuel consumption conversion constants (kWh or liters equivalent per unit)
DEFAULT_GASOLINE_CONVERSION: float = 9.2
DEFAULT_DIESEL_CONVERSION: float = 10.96

# Imperial to Metric Unit Conversion Constants
LBF_TO_N: float = 4.44822
MPH_TO_KPH: float = 1.60934
LBS_TO_KG: float = 0.453592
HP_TO_KW: float = 0.7457

# Fuel type mapping dictionary
FUEL_TYPE_MAPPING = {
    'Tier 2 Cert Gasoline': 'gasoline',
    'Cold CO Premium (CERT)': 'gasoline',
    'Cold CO Premium (Tier 2)': 'gasoline',
    'Electricity': 'electric',
    'Cold CO Regular (Tier 2)': 'gasoline',
    'E85 (85% Ethanol 15% EPA Unleaded Gasoline)': 'gasoline',
    'Federal Cert Diesel 7-15 PPM Sulfur': 'diesel',
    'Hydrogen 5': '-',
    'CARB LEV3 E10 Regular Gasoline': 'gasoline',
    'Cold CO E10 Regular Gasoline (Tier 3)': 'gasoline',
    'Tier 3 E10 Premium Gasoline (9 RVP @Low Alt.)': 'gasoline',
    'CARB Phase II Gasoline': 'gasoline',
    'Tier 3 E10 Regular Gasoline (9 RVP @Low Alt.)': 'gasoline',
    'CNG': '-',
    'EPA Unleaded Gasoline': 'gasoline',
    'LPG': '-',
}
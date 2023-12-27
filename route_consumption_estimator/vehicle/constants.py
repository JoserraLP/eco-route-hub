GRAVITY = 9.81  # Gravity

# Aerodynamic effect
RO = 1.225  # Air density in kg/m^3
CX = 0.28  # Aerodynamic coefficient

# Idling consumption = ralenti
IDLING_CONSUMPTION = 0.7

# Max acceleration limit
ACC_LIMIT_PROPORTION = 0.7*GRAVITY

# Area factor -> Defined by hand
AREA_FACTOR = 0.8

# Time
DELTA_T = 1

# Space
DELTA_S = 1

# Percentage value of maximum power for performance calculation according to FASTSIM
POWER_PERCENTAGE = [0, 0.5, 1.5, 4, 6, 10, 14, 20, 40, 60, 80, 100]

# Performance value according to FASTSIM
ENGINE_PERFORMANCE = [10, 14, 20, 26, 32, 39, 41, 42, 41, 38, 36, 34]

DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"

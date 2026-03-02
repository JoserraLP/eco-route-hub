import pandas as pd

from route_consumption_estimator.core.constants import *

# Load the Excel file
df = pd.read_excel('../../../vehicles/parsed_vehicles.xlsx')

vehicle_info = "('{name}', '{engine}', {mass}, {pmaxkw}, {conversion}, {factor}, {a}, {b}, {c}, '', ''),\n"

sql_commands = """

USE greta_app;

INSERT INTO vehicle (Name, MotorType, UnladenVehMass, PMaxKw, LitersConversion, ResistanceFactor, A, B, C, Url, ImageUrl)
VALUES 
"""

for index, row in df.iterrows():
    name = row['Represented Test Veh Make'] + '_-_' + row['Represented Test Veh Model']
    engine = str(row['Test Fuel Type Description']).upper()

    if engine == 'DIESEL':
        conversion = DEFAULT_DIESEL_CONVERSION
    elif engine == 'GASOLINE':
        conversion = DEFAULT_GASOLINE_CONVERSION
    else:
        conversion = -1.0

    mass = row['Equivalent Test Weight (kg)']
    pmaxkw = row['Rated Power (kW)']
    a = row['Target Coef A (N)']
    b = row['Target Coef B (N/kph)']
    c = row['Target Coef C (N/kph**2)']
    # Factor now is by default as is it not specified
    factor = DEFAULT_VEHICLE_RF
    sql_commands += vehicle_info.format(name=name, engine=engine, mass=mass, pmaxkw=pmaxkw, conversion=conversion,
                                        factor=factor, a=a, b=b, c=c)

# Remove the last ',' and add ;
sql_commands = sql_commands[:-2] + ';'

# Write the SQL commands to a file
with open('../../../../vehicles/vehicles_db.sql', 'w') as f:
    f.write(sql_commands)

import pandas as pd
import os
import glob

# Define the directory
directory = '../../../vehicles/'

# Get all csv and xlsx files in the directory
files = glob.glob(os.path.join(directory, '*.xlsx')) + glob.glob(os.path.join(directory, '*.csv'))

# Initialize a list to store DataFrames
dfs = []

for file in files:
    # Load the file
    if file.endswith('.xlsx'):
        df = pd.read_excel(file)
    else:
        df = pd.read_csv(file)

    # Keep only the specified columns and add 'Equivalent Test Weight (lbs.)'
    df = df[['Model Year', 'Represented Test Veh Make', 'Represented Test Veh Model', 'Rated Horsepower',
             'Target Coef A (lbf)', 'Target Coef B (lbf/mph)', 'Target Coef C (lbf/mph**2)', 'Test Fuel Type Description', 'Equivalent Test Weight (lbs.)']]

    # Convert the weight to kilograms
    # 1 lb = 0.453592 kg
    df['Equivalent Test Weight (kg)'] = df['Equivalent Test Weight (lbs.)'] * 0.453592

    # Convert the coefficients to European metrics
    df['Target Coef A (N)'] = df['Target Coef A (lbf)'] * 4.44822
    df['Target Coef B (N/kph)'] = df['Target Coef B (lbf/mph)'] * 4.44822 / 1.60934
    df['Target Coef C (N/kph**2)'] = df['Target Coef C (lbf/mph**2)'] * 4.44822 / (1.60934 ** 2)

    # Convert horsepower to kilowatts
    df['Rated Power (kW)'] = df['Rated Horsepower'] * 0.7457

    # Drop the old columns
    df = df.drop(columns=['Rated Horsepower', 'Target Coef A (lbf)', 'Target Coef B (lbf/mph)', 'Target Coef C (lbf/mph**2)', 'Equivalent Test Weight (lbs.)'])

    # Replace with fuel types
    fuel_type_mapping = {
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
        'LPG': '-'
    }

    # Replace the values
    df['Test Fuel Type Description'] = df['Test Fuel Type Description'].replace(fuel_type_mapping)

    # Append the DataFrame to the list
    dfs.append(df)

# Concatenate all DataFrames in the list
df_all = pd.concat(dfs, ignore_index=True)

# Remove the engines with -
df_all = df_all[df_all['Test Fuel Type Description'] != '-']

# Remove duplicates based on 'Represented Test Veh Make' and 'Represented Test Veh Model'
df_all = df_all.drop_duplicates(subset=['Represented Test Veh Make', 'Represented Test Veh Model'])

# Save the new DataFrame to a new Excel file
df_all.to_excel(directory + './parsed_vehicles.xlsx', index=False)

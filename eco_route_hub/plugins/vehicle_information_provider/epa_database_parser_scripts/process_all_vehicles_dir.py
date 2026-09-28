"""Processes EPA vehicle data files (CSV/XLSX) in a directory, converts units to SI metric

(N, N/(m/s), N/(m/s)^2), filters fuel types, and aggregates into a single parsed Excel output file.
"""

import logging
from pathlib import Path
from typing import List, Set
import pandas as pd

from eco_route_hub.plugins.vehicle_information_provider.epa_database_parser_scripts.constants import (
    FUEL_TYPE_MAPPING,
    HP_TO_KW,
    LBF_TO_N,
    LBS_TO_KG,
    MPH_TO_KPH,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path("vehicles_data")
OUTPUT_EXCEL = DATA_DIR / "parsed_vehicles.xlsx"
EXCLUDED_FILES: Set[str] = set()

REQUIRED_KEYS = [
    "Model Year",
    "Represented Test Veh Make",
    "Represented Test Veh Model",
    "Rated Horsepower",
    "Target Coef A (lbf)",
    "Target Coef B (lbf/mph)",
    "Target Coef C (lbf/mph**2)",
    "Test Fuel Type Description",
    "Equivalent Test Weight (lbs.)",
]


def process_vehicle_file(file_path: Path) -> pd.DataFrame:
    """Read and process a single EPA CSV or Excel file, converting road-load coefficients to SI units."""
    logger.info(f"Processing file: {file_path.name}")
    try:
        if file_path.suffix.lower() == ".xlsx":
            df = pd.read_excel(file_path)
        elif file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
        else:
            return pd.DataFrame()
    except Exception as err:
        logger.error(f"Error reading file {file_path}: {err}")
        return pd.DataFrame()

    if not set(REQUIRED_KEYS).issubset(df.columns):
        logger.warning(
            f"File '{file_path.name}' missing required EPA columns. Skipping."
        )
        return pd.DataFrame()

    # Filter columns and copy
    df = df[REQUIRED_KEYS].copy()

    # Conversion factor from mph to m/s (1 mph = 0.44704 m/s)
    mph_to_mps = MPH_TO_KPH / 3.6

    # Unit conversions to SI standard
    df["Equivalent Test Weight (kg)"] = df["Equivalent Test Weight (lbs.)"] * LBS_TO_KG
    df["Target Coef A (N)"] = df["Target Coef A (lbf)"] * LBF_TO_N

    # B: (lbf / mph) -> N / (m/s)
    df["Target Coef B (N/mps)"] = (
        df["Target Coef B (lbf/mph)"] * LBF_TO_N / mph_to_mps
    )

    # C: (lbf / mph**2) -> N / (m/s)**2
    df["Target Coef C (N/mps**2)"] = (
        df["Target Coef C (lbf/mph**2)"] * LBF_TO_N / (mph_to_mps**2)
    )

    df["Rated Power (kW)"] = df["Rated Horsepower"] * HP_TO_KW

    # Drop old imperial columns
    df = df.drop(
        columns=[
            "Rated Horsepower",
            "Target Coef A (lbf)",
            "Target Coef B (lbf/mph)",
            "Target Coef C (lbf/mph**2)",
            "Equivalent Test Weight (lbs.)",
        ]
    )

    # Normalize fuel type mapping
    df["Test Fuel Type Description"] = df["Test Fuel Type Description"].replace(
        FUEL_TYPE_MAPPING
    )

    return df


def aggregate_all_vehicles(
    input_dir: Path, output_file: Path, excluded_files: Set[str]
) -> None:
    """Process all vehicle data files in directory and output aggregated parsed Excel."""
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        return

    files = list(input_dir.glob("*.xlsx")) + list(input_dir.glob("*.csv"))
    dfs: List[pd.DataFrame] = []

    for file_path in files:
        if file_path.name in excluded_files or file_path.resolve() == output_file.resolve():
            continue

        processed_df = process_vehicle_file(file_path)
        if not processed_df.empty:
            dfs.append(processed_df)

    if not dfs:
        logger.warning("No valid vehicle datasets found to aggregate.")
        return

    df_all = pd.concat(dfs, ignore_index=True)

    # Filter unmapped/irrelevant engine types
    df_all = df_all[df_all["Test Fuel Type Description"] != "-"]

    # Drop duplicates by Make and Model
    df_all = df_all.drop_duplicates(
        subset=["Represented Test Veh Make", "Represented Test Veh Model"]
    )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    df_all.to_excel(output_file, index=False)
    logger.info(f"Successfully saved aggregated vehicles dataset to {output_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    aggregate_all_vehicles(DATA_DIR, OUTPUT_EXCEL, EXCLUDED_FILES)
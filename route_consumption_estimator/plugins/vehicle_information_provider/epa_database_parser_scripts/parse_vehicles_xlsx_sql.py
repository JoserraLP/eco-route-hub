"""
Generates an SQL script to insert parsed vehicle data into MySQL/MariaDB database.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from route_consumption_estimator.plugins.vehicle_information_provider.epa_database_parser_scripts.constants import (
    DEFAULT_DIESEL_CONVERSION,
    DEFAULT_GASOLINE_CONVERSION,
    DEFAULT_VEHICLE_RF,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path("vehicles_data")
INPUT_EXCEL = DATA_DIR / "parsed_vehicles.xlsx"
OUTPUT_SQL = DATA_DIR / "vehicles_db.sql"


def escape_sql_str(value: Any) -> str:
    """Escape single quotes for raw SQL string literals."""
    return str(value).strip().replace("'", "''")


def generate_sql_insert_script(input_path: Path, output_path: Path) -> None:
    """Read parsed Excel data and produce a safe SQL INSERT script."""
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    df = pd.read_excel(input_path)
    values_tuples = []

    for _, row in df.iterrows():
        make = str(row.get('Represented Test Veh Make', '')).strip()
        model = str(row.get('Represented Test Veh Model', '')).strip()
        raw_name = f"{make}_-_{model}"
        name = escape_sql_str(raw_name)

        engine = str(row.get('Test Fuel Type Description', '')).upper().strip()

        if engine == 'DIESEL':
            conversion = DEFAULT_DIESEL_CONVERSION
        elif engine == 'GASOLINE':
            conversion = DEFAULT_GASOLINE_CONVERSION
        else:
            conversion = -1.0

        mass = float(row.get('Equivalent Test Weight (kg)', 0.0) or 0.0)
        pmaxkw = float(row.get('Rated Power (kW)', 0.0) or 0.0)
        a = float(row.get('Target Coef A (N)', 0.0) or 0.0)
        b = float(row.get('Target Coef B (N/kph)', 0.0) or 0.0)
        c = float(row.get('Target Coef C (N/kph**2)', 0.0) or 0.0)
        factor = DEFAULT_VEHICLE_RF

        tuple_str = (
            f"('{name}', '{engine}', {mass:.2f}, {pmaxkw:.2f}, "
            f"{conversion:.2f}, {factor:.4f}, {a:.4f}, {b:.4f}, {c:.4f}, '', '')"
        )
        values_tuples.append(tuple_str)

    if not values_tuples:
        logger.warning("No vehicle rows processed for SQL script.")
        return

    sql_header = (
        "USE greta_app;\n\n"
        "INSERT INTO vehicle (Name, MotorType, UnladenVehMass, PMaxKw, LitersConversion, "
        "ResistanceFactor, A, B, C, Url, ImageUrl)\nVALUES\n"
    )

    full_sql = sql_header + ",\n".join(values_tuples) + ";\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_sql)

    logger.info(f"SQL file successfully generated at {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_sql_insert_script(INPUT_EXCEL, OUTPUT_SQL)

"""
Plotting utilities for route consumption analysis and model validation.
"""

import logging
from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


def show_consumption(
    consumption: List[float],
    title: str = "Energy Consumption Profile",
    save_path: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Plot energy consumption along route steps or micro-segments.

    Args:
        consumption (List[float]): Sequence of consumption values.
        title (str): Title for the plot.
        save_path (Optional[str]): File path to save the generated plot image.
        show (bool): Whether to display the plot interactively.
    """
    if not consumption:
        logger.warning("Empty consumption list provided for plotting.")
        return

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        range(len(consumption)),
        consumption,
        label="Consumption",
        color="tab:blue",
        linewidth=1.5,
    )
    ax.set_title(title)
    ax.set_xlabel("Micro-segment / Step")
    ax.set_ylabel("Consumption (kWh / L)")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
        logger.info(f"Consumption plot saved to {save_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def compare_consumption(
    engine_based_consumption: List[float],
    experiment_loaded_consumption: List[float],
    label_engine: str = "Estimator",
    label_experiment: str = "OBD Telemetry",
    title: str = "Consumption Comparison: Model vs OBD",
    save_path: Optional[str] = None,
    show: bool = True,
) -> None:
    """
    Compare and plot estimated consumption against real OBD telemetry data using 1D interpolation.

    Args:
        engine_based_consumption (List[float]): Model-estimated consumption values.
        experiment_loaded_consumption (List[float]): Measured OBD consumption values.
        label_engine (str): Legend label for model estimation.
        label_experiment (str): Legend label for measured experimental data.
        title (str): Plot title.
        save_path (Optional[str]): Optional file path to save the plot image.
        show (bool): Whether to show the interactive window.
    """
    if not engine_based_consumption or not experiment_loaded_consumption:
        logger.warning("One or both consumption series are empty.")
        return

    # Assign lists and map corresponding labels dynamically
    if len(engine_based_consumption) >= len(experiment_loaded_consumption):
        greater_list, shorter_list = (
            engine_based_consumption,
            experiment_loaded_consumption,
        )
        greater_label, shorter_label = label_engine, label_experiment
    else:
        greater_list, shorter_list = (
            experiment_loaded_consumption,
            engine_based_consumption,
        )
        greater_label, shorter_label = label_experiment, label_engine

    x_dense = np.linspace(0, 1, len(greater_list))
    x_sparse = np.linspace(0, 1, len(shorter_list))

    interp_shorter = np.interp(x_dense, x_sparse, shorter_list)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x_dense, greater_list, label=greater_label, linewidth=1.8)
    ax.plot(
        x_dense,
        interp_shorter,
        label=shorter_label,
        linestyle="--",
        linewidth=1.8,
    )
    ax.set_title(title)
    ax.set_xlabel("Normalized Distance / Route Progress (0 - 1)")
    ax.set_ylabel("Consumption")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend()

    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
        logger.info(f"Comparison plot saved to {save_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)

"""
FASTSim vehicle energy model plugin module.

Integrates the NREL FASTSim simulation engine with GRETA route and vehicle models,
handling spatial-to-temporal profile conversions and energy boundary extractions.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

from route_consumption_estimator.domain.route_model import RouteModel
from route_consumption_estimator.domain.vehicle_model import VehicleModel
from route_consumption_estimator.plugins.speed_profile_provider.speed_profile import SpeedProfile

try:
    from fastsim import cycle, simdrive, vehicle as fastsim_vehicle
    FASTSIM_AVAILABLE = True
except ImportError:
    FASTSIM_AVAILABLE = False
    cycle = None
    simdrive = None
    fastsim_vehicle = None

from route_consumption_estimator.interfaces import VehicleEnergyModelProvider

logger = logging.getLogger(__name__)

METERS_PER_MILE = 1609.344
KWH_PER_GGE = 33.7
LITERS_PER_GALLON = 3.785411784
AIR_DENSITY_KG_M3 = 1.2
GRAVITY_M_S2 = 9.81


def _integrate(y: np.ndarray, x: np.ndarray) -> float:
    """Perform trapezoidal integration compatible with NumPy 1.x and 2.x."""
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def _array(values: Any, name: str, allow_empty: bool = False) -> np.ndarray:
    """Convert and validate input into a 1D float NumPy array."""
    if values is None:
        if allow_empty:
            return np.asarray([], dtype=float)
        raise ValueError(f"{name} cannot be None.")

    result = np.reshape(np.asarray(values, dtype=float), -1)

    if np.size(result) == 0 and not allow_empty:
        raise ValueError(f"{name} cannot be empty.")

    if not np.all(np.isfinite(result)):
        indexes = np.flatnonzero(~np.isfinite(result))[:10].tolist()
        raise ValueError(
            f"{name} contains NaN or infinite values at indices {indexes}."
        )

    return result


def _optional_float(value: Any) -> Optional[float]:
    """Convert an optional scalar value to a JSON-compatible float."""
    if value is None:
        return None

    try:
        array = np.reshape(np.asarray(value, dtype=float), -1)
        if np.size(array) == 0:
            return None
        result = float(array[-1])
        return result if np.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def safe_getattr(obj: Any, attribute: str) -> Any:
    """Safely retrieve object attributes without raising exceptions."""
    try:
        return getattr(obj, attribute)
    except Exception as exc:
        return f"<ERROR reading {attribute}: {exc}>"


def summarize_value(value: Any, max_items: int = 8) -> Any:
    """Summarize scalars, lists, and arrays for logging output."""
    try:
        if isinstance(value, (list, tuple)):
            value = np.asarray(value)

        if isinstance(value, np.ndarray):
            result = {
                "type": "np.ndarray",
                "shape": value.shape,
                "dtype": str(value.dtype),
            }

            if value.size == 0:
                result["empty"] = True
                return result

            flattened = value.reshape(-1)
            result["first"] = flattened[:max_items].tolist()
            result["last"] = flattened[-max_items:].tolist()

            if np.issubdtype(value.dtype, np.number):
                numeric = value.astype(float, copy=False)
                result.update(
                    min=float(np.nanmin(numeric)),
                    mean=float(np.nanmean(numeric)),
                    max=float(np.nanmax(numeric)),
                    sum=float(np.nansum(numeric)),
                )

            return result

        if isinstance(value, (int, float, str, bool, type(None))):
            return value

        return f"<{type(value).__name__}>"
    except Exception as exc:
        return f"<ERROR summarizing value: {exc}>"


def inspect_vehicle(veh: Any) -> None:
    """Log vehicle attributes for debugging."""
    logger.debug("================ VEHICLE DEBUG ================")
    logger.debug(f"Object type: {type(veh)}")

    attributes = (
        "veh_pt_type", "veh_kg", "glider_kg", "cargo_kg",
        "fc_max_kw", "fc_fuel_type", "fc_peak_eff",
        "mc_max_kw", "ess_max_kw", "ess_max_kwh",
        "ess_init_soc", "ess_min_soc", "ess_max_soc",
        "trans_eff", "wheel_rr_coef", "wheel_radius_m",
        "drag_coef", "frontal_area_m2", "aux_kw",
        "fs_kwh", "fs_kwh_per_kg",
    )

    for attribute in attributes:
        if hasattr(veh, attribute):
            logger.debug(
                f"{attribute}: "
                f"{summarize_value(safe_getattr(veh, attribute))}"
            )

    logger.debug("================================================")


def inspect_simdrive(sd: Any) -> None:
    """Log SimDrive state for debugging."""
    logger.debug("================ SIMDRIVE DEBUG ================")
    keywords = (
        "mpg", "fuel", "fs", "fc", "kwh", "ess", "soc",
        "dist", "trace", "miss", "battery", "electric",
    )

    for attribute in dir(sd):
        if attribute.startswith("_"):
            continue
        if not any(key in attribute.lower() for key in keywords):
            continue

        try:
            value = getattr(sd, attribute)
            if not callable(value):
                logger.debug(f"{attribute}: {summarize_value(value)}")
        except Exception as exc:
            logger.debug(f"{attribute}: <ERROR {exc}>")

    logger.debug("================================================")


def get_vehicle_id(motor_type: str) -> int:
    """Map logical engine/motor type string to standard FASTSim database vehicle ID."""
    normalized = str(motor_type or "").strip().lower()
    return {
        "diesel": 9,
        "electric": 23,
        "ev": 23,
        "hybrid": 17,
    }.get(normalized, 1)


def _vehicle_motor_type(user_vehicle: VehicleModel) -> str:
    """Extract normalized motor type string from vehicle model."""
    for attribute in (
        "motor_type", "engine_type", "powertrain_type", "fuel_type"
    ):
        value = getattr(user_vehicle, attribute, None)
        if value is not None:
            return str(value).strip().lower()

    return "conventional"


def convert_vehicle_to_fastsim(user_vehicle: VehicleModel) -> Any:
    """Load base powertrain architecture from FASTSim and overwrite physical characteristics."""
    if not FASTSIM_AVAILABLE:
        raise ImportError(
            "FASTSim library is not installed or available in current environment."
        )

    motor_type = _vehicle_motor_type(user_vehicle)
    veh = fastsim_vehicle.Vehicle.from_vehdb(get_vehicle_id(motor_type))

    mass_kg = float(user_vehicle.total_mass)
    maximum_power_kw = float(user_vehicle.p_max_kw)
    coastdown_a_n = float(user_vehicle.A)
    coastdown_c_n_per_mps2 = float(user_vehicle.C)
    frontal_area_m2 = float(getattr(user_vehicle, "frontal_area_m2", 2.2))

    if mass_kg <= 0.0:
        raise ValueError("Vehicle mass must be positive.")
    if maximum_power_kw <= 0.0:
        raise ValueError("Maximum power must be positive.")
    if frontal_area_m2 <= 0.0:
        raise ValueError("Frontal area must be positive.")
    if coastdown_a_n < 0.0 or coastdown_c_n_per_mps2 < 0.0:
        raise ValueError("Coastdown coefficients A and C cannot be negative.")

    veh.veh_kg = mass_kg
    veh.wheel_rr_coef = coastdown_a_n / (mass_kg * GRAVITY_M_S2)
    veh.frontal_area_m2 = frontal_area_m2
    veh.drag_coef = (
        2.0 * coastdown_c_n_per_mps2
        / (AIR_DENSITY_KG_M3 * frontal_area_m2)
    )

    if motor_type in {"electric", "ev"}:
        if hasattr(veh, "mc_max_kw"):
            veh.mc_max_kw = maximum_power_kw
    elif hasattr(veh, "fc_max_kw"):
        veh.fc_max_kw = maximum_power_kw

    return veh


from typing import Tuple
import numpy as np


def _normalise_spatial_profile(
    speeds: np.ndarray,
    slopes_grade: np.ndarray,
    raw_distances: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Normalize spatial distance vectors, node speeds, and slope profiles.

    Handles size mismatches between speed and distance arrays (including +2 offsets
    and generic spatial structures).
    """
    number_of_speeds = speeds.size
    distance_differences = np.diff(raw_distances)

    cumulative_boundaries = (
        raw_distances.size == number_of_speeds + 1
        and np.isclose(raw_distances[0], 0.0, atol=1e-6)
        and np.all(distance_differences >= -1e-9)
        and np.any(distance_differences > 1e-9)
    )

    if cumulative_boundaries:
        segment_lengths = np.copy(distance_differences)
        segment_speeds = speeds.copy()
        mode = "segment_speeds_cumulative_boundaries"

    elif raw_distances.size == number_of_speeds - 1:
        segment_lengths = raw_distances.copy()
        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
        mode = "node_speeds_segment_lengths"

    elif raw_distances.size == number_of_speeds:
        if np.isclose(raw_distances[0], 0.0, atol=1e-9):
            segment_lengths = raw_distances[1:].copy()
        elif np.isclose(raw_distances[-1], 0.0, atol=1e-9):
            segment_lengths = raw_distances[:-1].copy()
        else:
            segment_lengths = 0.5 * (raw_distances[:-1] + raw_distances[1:])

        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
        mode = "node_speeds_one_padding_value"

    elif raw_distances.size == number_of_speeds + 1:
        segment_lengths = raw_distances[1:-1].copy()
        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
        mode = "node_speeds_two_padding_values"

    # Explicit handling for +2 distance values (e.g. 838 distances vs 836 speeds)
    elif raw_distances.size == number_of_speeds + 2:
        diffs = np.diff(raw_distances)

        # Case A: raw_distances are cumulative distances (838 points -> 837 deltas)
        if np.all(diffs >= -1e-9):
            # If speeds are node speeds (836 nodes -> 835 segments):
            # Trimming 1 element from each end of diffs yields 835 segments
            segment_lengths = diffs[1:-1].copy()
            segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
            mode = "cumulative_boundaries_with_two_padding_values"
        else:
            # Case B: raw_distances are increments with 3 padding values
            segment_lengths = raw_distances[1:-2].copy()
            segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
            mode = "node_speeds_three_padding_values"

    else:
        # ROBUST FALLBACK: Re-interpolate distances if spatial structure does not match standard patterns
        target_segments = max(1, number_of_speeds - 1)

        if np.all(distance_differences >= -1e-9):
            # Cumulative grid -> trim or re-interpolate to N-1 segments
            orig_cum = raw_distances - raw_distances[0]
            new_cum = np.linspace(0.0, orig_cum[-1], target_segments + 1)
            segment_lengths = np.diff(new_cum)
        else:
            # Re-interpolate distance vector directly
            orig_x = np.linspace(0.0, 1.0, raw_distances.size)
            new_x = np.linspace(0.0, 1.0, target_segments)
            segment_lengths = np.interp(new_x, orig_x, raw_distances)

        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
        mode = f"auto_resampled_fallback_{raw_distances.size}_to_{segment_speeds.size}"

    # Validate array length consistency
    if segment_lengths.size != segment_speeds.size:
        min_size = min(segment_lengths.size, segment_speeds.size)
        segment_lengths = segment_lengths[:min_size]
        segment_speeds = segment_speeds[:min_size]

    # Normalize slope profile
    if slopes_grade.size == 0:
        segment_slopes = np.zeros_like(segment_speeds)
    elif slopes_grade.size == segment_speeds.size:
        segment_slopes = slopes_grade.copy()
    elif slopes_grade.size == segment_speeds.size + 1:
        segment_slopes = 0.5 * (slopes_grade[:-1] + slopes_grade[1:])
    else:
        # Fallback for misaligned slope values
        orig_x = np.linspace(0.0, 1.0, slopes_grade.size)
        new_x = np.linspace(0.0, 1.0, segment_speeds.size)
        segment_slopes = np.interp(new_x, orig_x, slopes_grade)

    # Clean zero or negative values caused by floating-point inaccuracy
    segment_lengths[np.isclose(segment_lengths, 0.0, atol=1e-9)] = 0.0

    if np.any(segment_lengths < 0.0):
        indexes = np.flatnonzero(segment_lengths < 0.0)[:10].tolist()
        raise ValueError(f"Negative segment lengths found at indices {indexes}.")

    keep = segment_lengths > 0.0
    if not np.any(keep):
        raise ValueError(
            "Route contains no segments with positive length. "
            "Verify SpeedProfile populates segment_length properly."
        )

    return (
        segment_lengths[keep],
        segment_speeds[keep],
        segment_slopes[keep],
        mode,
    )


def _segment_to_boundaries(values: np.ndarray) -> np.ndarray:
    """Convert N segment-centered values to N+1 boundary values."""
    result = np.empty(values.size + 1, dtype=float)
    result[0] = values[0]
    result[-1] = values[-1]

    if values.size > 1:
        result[1:-1] = 0.5 * (values[:-1] + values[1:])

    return result


def debug_fastsim_cycle(cyc: Any) -> None:
    """Log FASTSim cycle summary parameters."""
    times = np.asarray(cyc.time_s, dtype=float)
    speeds = np.asarray(cyc.mps, dtype=float)
    duration_s = float(times[-1] - times[0])
    distance_m = _integrate(speeds, times)

    logger.debug("---------- DEBUG FASTSIM CYCLE ----------")
    logger.debug(f"Points: {np.size(times)}")
    logger.debug(f"Time span: {times[0]:.3f} .. {times[-1]:.3f} s")
    logger.debug(f"Duration: {duration_s:.3f} s")
    logger.debug(f"Distance: {distance_m:.3f} m")
    logger.debug(f"Mean speed: {distance_m / duration_s:.3f} m/s")
    logger.debug(f"Max speed: {np.max(speeds):.3f} m/s")
    logger.debug("-----------------------------------------")


class FastSimEnergyModel(VehicleEnergyModelProvider):
    """
    FASTSim energy model provider adapter with validated spatial-to-temporal drive cycle building.
    """

    def __init__(
        self,
        route: Optional[RouteModel] = None,
        vehicle: Optional[VehicleModel] = None,
    ) -> None:
        super().__init__(route, vehicle)
        self._speed_profile = SpeedProfile(
            route=self.route,
            vehicle=self.vehicle,
        )
        self.dt = 1.0
        self.minimum_moving_speed_mps = 0.5
        self.debug = False
        self._results: Optional[Dict[str, Any]] = None

    def load_route_and_vehicle(
        self,
        route: RouteModel,
        vehicle: VehicleModel,
    ) -> None:
        super().load_route_and_vehicle(route, vehicle)
        self._speed_profile = SpeedProfile(
            route=self.route,
            vehicle=self.vehicle,
        )
        self._results = None

    def _build_cycle(self) -> Any:
        if not FASTSIM_AVAILABLE:
            raise ImportError("FASTSim is not installed in the execution environment.")

        speeds = np.maximum(
            _array(self._speed_profile.speed_m_s, "speed_m_s"),
            0.0,
        )
        slopes_percent = _array(
            self._speed_profile.slope_t,
            "slope_t",
            allow_empty=True,
        )
        raw_distances = _array(
            self._speed_profile.segment_length,
            "segment_length",
        )

        logger.debug(f"Raw distances: {raw_distances}")

        if speeds.size < 2:
            raise ValueError("Speed profile requires at least two velocity points.")

        if slopes_percent.size and np.max(np.abs(slopes_percent)) > 100.0:
            raise ValueError("slope_t contains slope values greater than 100%.")

        slopes_grade = slopes_percent / 100.0

        (
            segment_lengths,
            segment_speeds,
            segment_slopes,
            spatial_mode,
        ) = _normalise_spatial_profile(
            speeds,
            slopes_grade,
            raw_distances,
        )

        expected_distance_m = float(np.sum(segment_lengths))
        effective_speeds = np.maximum(
            segment_speeds,
            self.minimum_moving_speed_mps,
        )
        segment_times = segment_lengths / effective_speeds

        if np.any(segment_times <= 0.0) or not np.all(np.isfinite(segment_times)):
            raise ValueError("Invalid segment duration times computed.")

        cumulative_time = np.concatenate(([0.0], np.cumsum(segment_times)))
        total_time_s = float(cumulative_time[-1])

        boundary_speeds = _segment_to_boundaries(segment_speeds)
        boundary_slopes = _segment_to_boundaries(segment_slopes)

        if not np.isfinite(self.dt) or self.dt <= 0.0:
            raise ValueError(f"self.dt must be strictly positive: {self.dt}.")

        times = np.arange(0.0, total_time_s, self.dt, dtype=float)
        if np.size(times) == 0 or not np.isclose(times[-1], total_time_s):
            times = np.append(times, total_time_s)

        speed_mps = np.interp(times, cumulative_time, boundary_speeds)
        slope_series = np.interp(times, cumulative_time, boundary_slopes)
        road_type = np.zeros(np.size(times), dtype=int)

        cyc = cycle.Cycle(
            times,
            speed_mps,
            slope_series,
            road_type,
            "custom_cycle",
        )

        self._validate_cycle(cyc, expected_distance_m)

        if self.debug:
            logger.debug(f"Spatial mode: {spatial_mode}")
            logger.debug(
                f"Original slope: {np.min(slopes_percent, initial=0.0):.3f}% .. "
                f"{np.max(slopes_percent, initial=0.0):.3f}%"
            )
            debug_fastsim_cycle(cyc)

        return cyc

    @staticmethod
    def _validate_cycle(
        cyc: Any,
        expected_distance_m: float,
        max_error_fraction: float = 0.02,
    ) -> None:
        times = _array(cyc.time_s, "cyc.time_s")
        speeds = _array(cyc.mps, "cyc.mps")

        if times.size != speeds.size or times.size < 2:
            raise ValueError("Cycle time and speed arrays must have equal length.")

        if np.any(np.diff(times) <= 0.0):
            raise ValueError("Cycle time steps must be strictly monotonically increasing.")

        simulated_distance_m = _integrate(speeds, times)
        error_fraction = (
            simulated_distance_m - expected_distance_m
        ) / expected_distance_m

        if abs(error_fraction) > max_error_fraction:
            raise ValueError(
                "Cycle resampling failed distance conservation threshold: "
                f"expected={expected_distance_m:.3f} m, "
                f"simulated={simulated_distance_m:.3f} m, "
                f"error={100.0 * error_fraction:.3f}%."
            )

    def perform_speed_profile_processing(self) -> None:
        self._speed_profile.calculate_acceleration()
        self._speed_profile.calculate_resistances()
        self._speed_profile.calculate_gravitational_resistances()

    def perform_speed_profile_estimation(self) -> None:
        self._speed_profile.estimate_speed_profile()
        self.perform_speed_profile_processing()

    def perform_power_energy_consumption_calculation(self) -> Dict[str, Any]:
        cyc = self._build_cycle()
        veh = convert_vehicle_to_fastsim(self.vehicle)

        if self.debug:
            inspect_vehicle(veh)

        simulation = simdrive.SimDrive(cyc, veh)
        initial_soc = float(getattr(veh, "ess_init_soc", 0.6) or 0.6)
        simulation.sim_drive(init_soc=initial_soc)

        if self.debug:
            inspect_simdrive(simulation)

        self._results = self.extract_consumption_summary(simulation)
        return self._results

    def retrieve_estimations(self) -> Optional[Dict[str, Any]]:
        return self._results

    @staticmethod
    def _cycle(sd: Any) -> Any:
        cyc = getattr(sd, "cyc", None)
        if cyc is None:
            cyc = getattr(sd, "cyc0", None)
        if cyc is None:
            raise ValueError("SimDrive instance missing 'cyc' or 'cyc0' attributes.")
        return cyc

    @classmethod
    def _distance_m(cls, sd: Any) -> float:
        cyc = cls._cycle(sd)

        if hasattr(sd, "mps_ach") and hasattr(cyc, "time_s"):
            return _integrate(
                np.asarray(sd.mps_ach, dtype=float),
                np.asarray(cyc.time_s, dtype=float),
            )

        if hasattr(sd, "dist_mi"):
            return float(
                np.sum(np.asarray(sd.dist_mi, dtype=float)) * METERS_PER_MILE
            )

        if hasattr(sd, "dist_m"):
            return float(np.sum(np.asarray(sd.dist_m, dtype=float)))

        if hasattr(cyc, "mps") and hasattr(cyc, "time_s"):
            return _integrate(
                np.asarray(cyc.mps, dtype=float),
                np.asarray(cyc.time_s, dtype=float),
            )

        raise ValueError("Unable to resolve simulated distance from SimDrive.")

    @staticmethod
    def _fuel_energy_kwh(sd: Any) -> Optional[float]:
        if hasattr(sd, "fs_kwh_out_ach"):
            return float(np.sum(np.asarray(sd.fs_kwh_out_ach, dtype=float)))

        if hasattr(sd, "fuel_kj"):
            return float(sd.fuel_kj) / 3600.0

        if hasattr(sd, "fs_cumu_mj_out_ach"):
            values = np.asarray(sd.fs_cumu_mj_out_ach, dtype=float)
            return float(values[-1]) / 3.6 if np.size(values) else None

        return None

    @staticmethod
    def _battery_energy_kwh(sd: Any) -> Optional[float]:
        for attribute in ("ess_kwh_out_ach", "battery_kwh_out_ach"):
            if hasattr(sd, attribute):
                return float(
                    np.sum(np.asarray(getattr(sd, attribute), dtype=float))
                )

        return None

    def extract_consumption_summary(self, sd: Any) -> Dict[str, Any]:
        """Extract simulation output energy and distance metrics into standard dictionary format."""
        cyc = self._cycle(sd)
        times = _array(cyc.time_s, "cyc.time_s")

        if times.size < 2:
            raise ValueError("Cycle must contain at least two timestamps.")

        time_differences = np.diff(times)
        if np.any(time_differences <= 0.0):
            raise ValueError("Cycle timestamps must be strictly increasing.")

        time_s = float(times[-1] - times[0])
        distance_m = self._distance_m(sd)
        distance_km = distance_m / 1000.0
        time_h = time_s / 3600.0

        if distance_km <= 0.0:
            raise ValueError(f"Invalid FASTSim distance: {distance_m} m.")
        if time_h <= 0.0:
            raise ValueError(f"Invalid FASTSim time span: {time_s} s.")

        motor_type = _vehicle_motor_type(self.vehicle)
        is_ev = motor_type in {"electric", "ev"}

        if is_ev:
            energy_kwh = self._battery_energy_kwh(sd)

            if energy_kwh is None:
                specific = getattr(sd, "battery_kwh_per_mi", None)
                if specific is None:
                    specific = getattr(sd, "electric_kwh_per_mi", None)
                if specific is not None:
                    distance_miles = distance_m / METERS_PER_MILE
                    energy_kwh = float(specific) * distance_miles

            if energy_kwh is None:
                raise ValueError("No battery energy attributes found in SimDrive output.")

            energy_source = "battery"
            energy_boundary = "battery_output"
            energy_consumption = float(energy_kwh)
            consumption_unit = "kWh"
            total_liters_equivalent = None
            liters_equivalent_per_100_km = None

        else:
            energy_kwh = self._fuel_energy_kwh(sd)

            if energy_kwh is None:
                raise ValueError("No fuel energy attributes found in SimDrive output.")

            total_liters_equivalent = (
                float(energy_kwh) / KWH_PER_GGE * LITERS_PER_GALLON
            )
            liters_equivalent_per_100_km = (
                total_liters_equivalent / distance_km * 100.0
            )
            energy_source = "fuel"
            energy_boundary = "fuel_storage_output"
            energy_consumption = total_liters_equivalent
            consumption_unit = "L_gasoline_equivalent"

        energy_kwh = float(energy_kwh)
        if not np.isfinite(energy_kwh) or energy_kwh < 0.0:
            raise ValueError(f"Invalid FASTSim energy output: {energy_kwh} kWh.")

        avg_speed_kmh = distance_km / time_h
        kwh_per_100_km = energy_kwh / distance_km * 100.0
        wh_per_km = energy_kwh * 1000.0 / distance_km
        distance_time_ratio = distance_m / time_s

        possible_distance_as_time = bool(
            distance_m > 100.0 and abs(time_s - distance_m) / distance_m < 0.02
        )

        result: Dict[str, Any] = {
            "energyConsumption": float(energy_consumption),
            "energyConsumptionUnit": consumption_unit,
            "energyKwh": energy_kwh,
            "energyUnit": "kWh",
            "energySource": energy_source,
            "energyBoundary": energy_boundary,
            "distance": float(distance_m),
            "distanceUnit": "m",
            "distanceKm": float(distance_km),
            "time": float(time_s),
            "timeUnit": "s",
            "avgSpeedKmh": float(avg_speed_kmh),
            "kwhPer100Km": float(kwh_per_100_km),
            "whPerKm": float(wh_per_km),
            "traceMiss": _optional_float(getattr(sd, "trace_miss", None)),
            "traceMissDistanceFraction": _optional_float(
                getattr(sd, "trace_miss_dist_frac", None)
            ),
            "cycleDiagnostics": {
                "startTimeS": float(times[0]),
                "endTimeS": float(times[-1]),
                "durationS": float(time_s),
                "minimumTimeStepS": float(np.min(time_differences)),
                "maximumTimeStepS": float(np.max(time_differences)),
                "meanTimeStepS": float(np.mean(time_differences)),
                "sampleCount": int(times.size),
                "distanceTimeRatioMps": float(distance_time_ratio),
                "possibleDistanceUsedAsTime": possible_distance_as_time,
            },
        }

        if is_ev:
            result.update(
                {
                    "batteryEnergyKwh": energy_kwh,
                    "batteryKwhPer100Km": float(kwh_per_100_km),
                    "batteryWhPerKm": float(wh_per_km),
                    "fuelEnergyKwh": None,
                    "fuelLiters": None,
                    "fuelLitersPer100Km": None,
                    "fuelEnergyKwhPer100Km": None,
                }
            )
        else:
            result.update(
                {
                    "fuelEnergyKwh": energy_kwh,
                    "fuelLiters": float(total_liters_equivalent),
                    "fuelLitersPer100Km": float(liters_equivalent_per_100_km),
                    "fuelEnergyKwhPer100Km": float(kwh_per_100_km),
                    "batteryEnergyKwh": None,
                    "batteryKwhPer100Km": None,
                    "batteryWhPerKm": None,
                }
            )

        return result

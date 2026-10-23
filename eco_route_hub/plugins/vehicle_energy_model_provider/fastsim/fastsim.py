"""
FASTSim vehicle energy model plugin module.

Integrates the NREL FASTSim simulation engine with EcoRouteHub route and vehicle models,
handling spatial-to-temporal profile conversions and energy boundary extractions.
"""

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

from eco_route_hub.domain.route_model import RouteModel
from eco_route_hub.domain.vehicle_model import VehicleModel
from eco_route_hub.plugins.speed_profile_provider.speed_profile import SpeedProfile

try:
    from fastsim import cycle, simdrive, vehicle as fastsim_vehicle

    FASTSIM_AVAILABLE = True
except ImportError:
    FASTSIM_AVAILABLE = False
    cycle = None
    simdrive = None
    fastsim_vehicle = None

from eco_route_hub.interfaces import VehicleEnergyModelProvider

logger = logging.getLogger(__name__)

METERS_PER_MILE = 1609.344
AIR_DENSITY_KG_M3 = 1.2
GRAVITY_M_S2 = 9.81


def _align_to_xp(xp: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """
    Ensure array fp has the exact same length as xp for 1D linear interpolation (np.interp).

    Args:
        xp (np.ndarray): Target x-coordinates array.
        fp (np.ndarray): Data points array to align or resample.

    Returns:
        np.ndarray: Array aligned to the length of xp, resampled or padded if necessary.
    """
    if fp is None or fp.size == 0:
        return np.zeros_like(xp, dtype=float)
    if fp.size == xp.size:
        return fp.astype(float, copy=False)
    if fp.size == xp.size - 1:
        # Convert N segment values to N+1 boundary values
        return _segment_to_boundaries(fp)

    # Generic resampling if array lengths differ
    orig_x = np.linspace(0.0, 1.0, fp.size)
    target_x = np.linspace(0.0, 1.0, xp.size)
    return np.interp(target_x, orig_x, fp)


def _integrate(y: np.ndarray, x: np.ndarray) -> float:
    """
    Perform trapezoidal numerical integration compatible across NumPy versions (1.x and 2.x).

    Args:
        y (np.ndarray): Input array to integrate.
        x (np.ndarray): Sample points corresponding to the y values.

    Returns:
        float: Definite integral estimated via the trapezoidal rule.
    """
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def _array(values: Any, name: str, allow_empty: bool = False) -> np.ndarray:
    """
    Convert and validate input data into a 1D float NumPy array.

    Args:
        values (Any): Input object (list, scalar, array, etc.) to convert.
        name (str): Variable identifier name for error message context.
        allow_empty (bool, optional): If True, allows returning an empty array.
            Defaults to False.

    Returns:
        np.ndarray: A 1D float NumPy array.

    Raises:
        ValueError: If values is None, empty when allow_empty is False, or contains NaN/Inf values.
    """
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
    """
    Convert an optional scalar value into a JSON-compatible float.

    Args:
        value (Any): Input scalar, list, or array element to convert.

    Returns:
        Optional[float]: Converted finite float value, or None if conversion fails or input is None/empty.
    """
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
    """
    Safely retrieve object attributes without raising exceptions during execution.

    Args:
        obj (Any): Target object instance.
        attribute (str): Name of the attribute to inspect.

    Returns:
        Any: Attribute value if accessible, or an error string if an exception occurs.
    """
    try:
        return getattr(obj, attribute)
    except Exception as exc:
        return f"<ERROR reading {attribute}: {exc}>"


def summarize_value(value: Any, max_items: int = 8) -> Any:
    """
    Summarize scalars, collections, and NumPy arrays for structured logging output.

    Args:
        value (Any): Input object or array to summarize.
        max_items (int, optional): Maximum number of initial/terminal elements to log for arrays.
            Defaults to 8.

    Returns:
        Any: Structured dictionary for arrays, primitive value for scalars, or class type representation string.
    """
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
    """
    Log vehicle physical and powertrain attributes for debugging purposes.

    Args:
        veh (Any): FASTSim vehicle model instance to inspect.
    """
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
    """
    Log SimDrive simulation states and key diagnostic fields for debugging.

    Args:
        sd (Any): FASTSim SimDrive engine instance to inspect.
    """
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
    """
    Map a logical engine or motor type string to a standard FASTSim database vehicle ID.

    Args:
        motor_type (str): Powertrain type identifier (e.g., 'diesel', 'electric', 'ev', 'hybrid').

    Returns:
        int: Corresponding FASTSim vehicle database ID.
    """
    normalized = str(motor_type or "").strip().lower()
    return {
        "diesel": 9,
        "electric": 23,
        "ev": 23,
        "hybrid": 17,
    }.get(normalized, 1)


def _vehicle_motor_type(user_vehicle: VehicleModel) -> str:
    """
    Extract and normalize the motor type string from a vehicle model instance.

    Args:
        user_vehicle (VehicleModel): Domain vehicle model to inspect.

    Returns:
        str: Normalized lowercase powertrain identifier string (defaults to 'conventional').
    """
    for attribute in (
            "motor_type", "engine_type", "powertrain_type", "fuel_type"
    ):
        value = getattr(user_vehicle, attribute, None)
        if value is not None:
            return str(value).strip().lower()

    return "conventional"


def convert_vehicle_to_fastsim(user_vehicle: VehicleModel) -> Any:
    """
    Convert a EcoRouteHub VehicleModel instance into a FASTSim Vehicle object.

    Maps vehicle mass, motor peak power, auxiliary electrical loads, and coastdown
    aerodynamic/rolling coefficients from EcoRouteHub to FASTSim formats.

    Args:
        user_vehicle (VehicleModel): Input vehicle model containing physical parameters.

    Returns:
        Any: Configured FASTSim vehicle object instance.

    Raises:
        ImportError: If the FASTSim library is not installed in the current environment.
    """
    if not FASTSIM_AVAILABLE:
        raise ImportError("FASTSim library is not installed.")

    motor_type = _vehicle_motor_type(user_vehicle)
    veh = fastsim_vehicle.Vehicle.from_vehdb(get_vehicle_id(motor_type))

    mass_kg = float(user_vehicle.total_mass)
    maximum_power_kw = float(user_vehicle.p_max_kw)
    coastdown_a_n = float(user_vehicle.A)

    # C in EcoRouteHub is provided in N/(km/h)^2 -> Convert to N/(m/s)^2 by multiplying by 3.6^2 (12.96)
    coastdown_c_kmh2 = float(user_vehicle.C)
    coastdown_c_mps2 = coastdown_c_kmh2 * (3.6 ** 2)

    frontal_area_m2 = float(getattr(user_vehicle, "frontal_area_m2", 2.2))

    veh.veh_kg = mass_kg
    veh.wheel_rr_coef = coastdown_a_n / (mass_kg * GRAVITY_M_S2)
    veh.frontal_area_m2 = frontal_area_m2

    # Correct Cd assignment (~0.324)
    veh.drag_coef = (
            2.0 * coastdown_c_mps2 / (AIR_DENSITY_KG_M3 * frontal_area_m2)
    )

    # Real auxiliary loads (e.g., HVAC, lights)
    if hasattr(veh, "aux_kw"):
        veh.aux_kw = float(getattr(user_vehicle, "aux_kw", 0.7))

    if motor_type in {"electric", "ev"}:
        if hasattr(veh, "mc_max_kw"):
            veh.mc_max_kw = maximum_power_kw
    elif hasattr(veh, "fc_max_kw"):
        veh.fc_max_kw = maximum_power_kw

    return veh


def _normalise_spatial_profile(
        speeds: np.ndarray,
        slopes_grade: np.ndarray,
        raw_distances: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]:
    """
    Normalize spatial distance vectors, node speeds, and slope grade profiles.

    Ensures consistent sizing across segment lengths, segment speeds, node speeds,
    and road slopes regardless of spatial boundary input formats.

    Args:
        speeds (np.ndarray): Array of vehicle speeds along the route.
        slopes_grade (np.ndarray): Array of road slopes in grade ratio/percentage.
        raw_distances (np.ndarray): Array of raw spatial distances or node coordinates.

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, str]: A tuple containing:
            - segment_lengths (np.ndarray): Segment length values in meters.
            - segment_speeds (np.ndarray): Speeds evaluated at segment centers.
            - node_speeds (np.ndarray): Speeds evaluated at segment boundary nodes.
            - segment_slopes (np.ndarray): Road slope values matched to segments.
            - mode (str): Descriptive key indicating the spatial normalization case applied.

    Raises:
        ValueError: If the route contains no segments with positive length.
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
        # Case A: N+1 accumulated node coordinates for N segment speeds
        segment_lengths = np.copy(distance_differences)
        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:]) if speeds.size > 1 else speeds.copy()
        node_speeds = speeds.copy()
        mode = "segment_speeds_cumulative_boundaries"

    elif raw_distances.size == number_of_speeds - 1:
        # Case B: N-1 segment lengths for N node speeds
        segment_lengths = raw_distances.copy()
        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
        node_speeds = speeds.copy()
        mode = "node_speeds_segment_lengths"

    elif raw_distances.size == number_of_speeds:
        # Case C: Equal sizes
        if np.isclose(raw_distances[0], 0.0, atol=1e-9) and np.all(distance_differences >= -1e-9):
            # Accumulated coordinates of N nodes
            segment_lengths = distance_differences.copy()
            segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
            node_speeds = speeds.copy()
            mode = "cumulative_nodes_matching_size"
        else:
            # CORRECTION: N segment lengths for N segment speeds
            segment_lengths = raw_distances.copy()
            segment_speeds = speeds.copy()
            node_speeds = _segment_to_boundaries(speeds)
            mode = "segment_lengths_matching_segment_speeds"

    else:
        # Fallback preserving total cumulative route distance
        target_segments = max(1, number_of_speeds - 1)
        if np.all(distance_differences >= -1e-9) and raw_distances.size > 1:
            total_dist = float(raw_distances[-1] - raw_distances[0])
        else:
            total_dist = float(np.sum(raw_distances))

        segment_lengths = np.full(target_segments, total_dist / target_segments)
        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:]) if speeds.size > 1 else speeds.copy()
        node_speeds = speeds.copy()
        mode = f"fallback_equal_segments_{target_segments}"

    # Clean zero or invalid values
    segment_lengths[np.isclose(segment_lengths, 0.0, atol=1e-9)] = 0.0
    keep = segment_lengths > 0.0
    if not np.any(keep):
        raise ValueError("Route contains no segments with positive length.")

    segment_lengths = segment_lengths[keep]
    segment_speeds = segment_speeds[keep]

    # Adjust slope profile
    if slopes_grade.size == 0:
        segment_slopes = np.zeros(segment_speeds.size)
    elif slopes_grade.size == segment_speeds.size:
        segment_slopes = slopes_grade[keep].copy()
    else:
        orig_x = np.linspace(0.0, 1.0, slopes_grade.size)
        new_x = np.linspace(0.0, 1.0, segment_speeds.size)
        segment_slopes = np.interp(new_x, orig_x, slopes_grade)

    return (
        segment_lengths,
        segment_speeds,
        node_speeds,
        segment_slopes,
        mode,
    )


def _segment_to_boundaries(values: np.ndarray) -> np.ndarray:
    """
    Convert N segment-centered values to N+1 boundary values using linear averaging.

    Args:
        values (np.ndarray): Array of segment-centered values of length N.

    Returns:
        np.ndarray: Array of boundary values of length N+1.
    """
    result = np.empty(values.size + 1, dtype=float)
    result[0] = values[0]
    result[-1] = values[-1]

    if values.size > 1:
        result[1:-1] = 0.5 * (values[:-1] + values[1:])

    return result


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
        self.speed_profile = SpeedProfile(
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
        self.speed_profile = SpeedProfile(
            route=self.route,
            vehicle=self.vehicle,
        )
        self._results = None

    def _get_canonical_route_distance(self, fallback_distance: float) -> float:
        """
        Exhaustively extract the actual spatial route distance in meters from the RouteModel object.

        Inspects direct attributes, segment collections, metadata dictionaries, and
        associated speed profile properties before defaulting to a fallback value.

        Args:
            fallback_distance (float): Default distance in meters to return if no valid
                route distance can be resolved.

        Returns:
            float: Extracted spatial distance in meters, or fallback_distance if resolution fails.
        """
        route_obj = self.route
        if route_obj is None and hasattr(self, "speed_profile") and self.speed_profile is not None:
            route_obj = getattr(self.speed_profile, "route", None)

        if route_obj is not None:
            # 1. Check direct attributes on RouteModel
            for attr in (
                    "total_distance", "total_distance_m", "distance_m", "distance",
                    "length_m", "total_length", "total_length_m", "length",
                    "route_length", "spatial_length", "distance_km", "length_km"
            ):
                val = getattr(route_obj, attr, None)
                if val is not None:
                    if callable(val):
                        try:
                            val = val()
                        except Exception:
                            continue
                    try:
                        num_val = float(val)
                        if num_val > 0:
                            if attr in ("distance_km", "length_km") or (num_val < 500.0 and fallback_distance > 1000.0):
                                num_val *= 1000.0
                            return num_val
                    except (ValueError, TypeError):
                        pass

            # 2. Check if RouteModel contains lists of segments/edges
            for coll_attr in ("segments", "edges", "links", "path", "features", "sub_routes"):
                collection = getattr(route_obj, coll_attr, None)
                if collection is not None and isinstance(collection, (list, tuple)) and len(collection) > 0:
                    try:
                        tot = 0.0
                        for item in collection:
                            if isinstance(item, dict):
                                item_len = item.get("length") or item.get("distance") or item.get(
                                    "segment_length") or item.get("distance_m") or 0.0
                            else:
                                item_len = (
                                        getattr(item, "length", None)
                                        or getattr(item, "distance", None)
                                        or getattr(item, "segment_length", None)
                                        or getattr(item, "distance_m", None)
                                        or getattr(item, "length_m", None)
                                        or 0.0
                                )
                                if callable(item_len):
                                    item_len = item_len()
                            tot += float(item_len)
                        if tot > 0:
                            return tot
                    except Exception:
                        pass

            # 3. Check metadata or summary dictionaries
            for meta_attr in ("summary", "metadata", "properties", "info"):
                meta = getattr(route_obj, meta_attr, None)
                if isinstance(meta, dict):
                    for key in ("distance", "total_distance", "length", "distance_m", "length_m"):
                        if key in meta:
                            try:
                                num_val = float(meta[key])
                                if num_val > 0:
                                    return num_val
                            except (ValueError, TypeError):
                                pass

        # If not found in RouteModel, check if SpeedProfile has a distance attribute or method
        if hasattr(self, "speed_profile") and self.speed_profile is not None:
            for sp_attr in ("route_distance", "total_distance", "target_distance"):
                val = getattr(self.speed_profile, sp_attr, None)
                if val is not None and isinstance(val, (int, float, np.number)) and val > 0:
                    return float(val)

        return fallback_distance

    def _build_cycle(self) -> Any:
        """
        Build and validate a FASTSim drive cycle from spatial or temporal speed and slope profiles.

        Processes speed, slope, and spatial distance data, interpolates them to a fixed
        time resolution (self.dt), rescales speed values to conserve total route distance,
        and returns a validated FASTSim Cycle instance.

        Returns:
            Any: Configured FASTSim Cycle instance (`fastsim.cycle.Cycle`).

        Raises:
            ImportError: If FASTSim library is not installed in the environment.
            ValueError: If resampled cycle validation fails distance conservation checks.
        """
        if not FASTSIM_AVAILABLE:
            raise ImportError("FASTSim is not installed in the execution environment.")

        # 1. Get real timestamps
        real_times = getattr(self.speed_profile, "time_s", None)
        if real_times is None and hasattr(self.route, "time_s"):
            real_times = getattr(self.route, "time_s")
        if real_times is None and hasattr(self.speed_profile, "time") and self.speed_profile.time is not None:
            real_times = self.speed_profile.time

        speeds = np.maximum(
            _array(self.speed_profile.speed_m_s, "speed_m_s"),
            0.0,
        )
        slopes_percent = _array(
            self.speed_profile.slope_t,
            "slope_t",
            allow_empty=True,
        )

        if np.count_nonzero(self.speed_profile.segment_length) == 0:
            self.speed_profile.calculate_segment_lengths()

        raw_distances = _array(self.speed_profile.segment_length, "segment_length", allow_empty=True)

        # Base integrated distance calculated from speed profile (e.g., 5918.80 m)
        raw_dist_sum = float(np.sum(raw_distances)) if raw_distances.size else 0.0

        # Actual canonical map route distance (e.g., 5939.46 m)
        expected_distance_m = self._get_canonical_route_distance(fallback_distance=raw_dist_sum)

        # 2. Temporal cycle construction
        if real_times is not None and len(real_times) == speeds.size:
            raw_times = _array(real_times, "time_s")
            cumulative_time = raw_times - raw_times[0]
            total_time_s = float(cumulative_time[-1])

            raw_speeds = speeds
            raw_slopes = slopes_percent / 100.0 if slopes_percent.size else np.zeros_like(speeds)

        else:
            slopes_grade = slopes_percent / 100.0 if slopes_percent.size else np.array([])

            (
                segment_lengths,
                segment_speeds,
                node_speeds,
                segment_slopes,
                spatial_mode,
            ) = _normalise_spatial_profile(speeds, slopes_grade, raw_distances)

            if expected_distance_m <= 0.0:
                expected_distance_m = float(np.sum(segment_lengths))

            effective_speeds = np.maximum(segment_speeds, self.minimum_moving_speed_mps)
            segment_times = segment_lengths / effective_speeds

            cumulative_time = np.concatenate(([0.0], np.cumsum(segment_times)))
            total_time_s = float(cumulative_time[-1])
            raw_speeds = node_speeds
            raw_slopes = segment_slopes

        # 3. Interpolate to fixed resolution self.dt (1.0 s)
        boundary_speeds = _align_to_xp(cumulative_time, raw_speeds)
        boundary_slopes = _align_to_xp(cumulative_time, raw_slopes)

        times = np.arange(0.0, total_time_s, self.dt, dtype=float)
        if np.size(times) == 0 or not np.isclose(times[-1], total_time_s):
            times = np.append(times, total_time_s)

        speed_mps = np.interp(times, cumulative_time, boundary_speeds)
        slope_series = np.interp(times, cumulative_time, boundary_slopes)

        # 4. MANDATORY RESCALING: Adjust speed curve so integral matches target distance
        simulated_distance_m = _integrate(speed_mps, times)
        if simulated_distance_m > 1e-6 and expected_distance_m > 1e-6:
            speed_mps *= (expected_distance_m / simulated_distance_m)

        road_type = np.zeros(np.size(times), dtype=int)

        cyc = cycle.Cycle(
            times,
            speed_mps,
            slope_series,
            road_type,
            "custom_cycle",
        )

        self._validate_cycle(cyc, expected_distance_m)
        return cyc

    @staticmethod
    def _validate_cycle(
            cyc: Any,
            expected_distance_m: float,
            max_error_fraction: float = 0.02,
    ) -> None:
        """
        Validate drive cycle temporal monotonicity and distance conservation threshold.

        Verifies that time and speed arrays have equal length, timestamps are strictly
        monotonically increasing, and total integrated distance matches expected distance
        within the allowed relative error fraction.

        Args:
            cyc (Any): FASTSim Cycle instance containing `time_s` and `mps` attributes.
            expected_distance_m (float): Target or canonical route distance in meters.
            max_error_fraction (float, optional): Maximum allowable relative error fraction
                for distance conservation. Defaults to 0.02 (2%).

        Raises:
            ValueError: If time and speed array lengths differ, timestamps are not strictly
                increasing, or distance integration error exceeds `max_error_fraction`.
        """
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
        self.speed_profile.calculate_acceleration()
        self.speed_profile.calculate_resistances()
        self.speed_profile.calculate_gravitational_resistances()

    def perform_speed_profile_estimation(self) -> None:
        self.speed_profile.estimate_speed_profile()
        self.perform_speed_profile_processing()

    def perform_power_energy_consumption_calculation(self) -> Dict[str, Any]:
        cyc = self._build_cycle()
        veh = convert_vehicle_to_fastsim(self.vehicle)
        # inspect_vehicle(veh)

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
                    float(energy_kwh) / self.vehicle.liters_conversion
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

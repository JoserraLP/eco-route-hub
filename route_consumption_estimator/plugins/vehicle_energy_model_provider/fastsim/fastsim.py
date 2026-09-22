from typing import Any, Dict, Optional, Tuple

import numpy as np
from fastsim import cycle, simdrive, vehicle as fastsim_vehicle

from route_consumption_estimator.domain.route_model import RouteModel
from route_consumption_estimator.domain.vehicle_model import VehicleModel
from route_consumption_estimator.interfaces import VehicleEnergyModelProvider
from route_consumption_estimator.plugins.speed_profile_provider.speed_profile import SpeedProfile


METERS_PER_MILE = 1609.344
KWH_PER_GGE = 33.7
LITERS_PER_GALLON = 3.785411784
AIR_DENSITY_KG_M3 = 1.2
GRAVITY_M_S2 = 9.81


def _array(values: Any, name: str, allow_empty: bool = False) -> np.ndarray:
    """Convierte una entrada en un vector float unidimensional validado."""
    if values is None:
        if allow_empty:
            return np.asarray([], dtype=float)
        raise ValueError(f"{name} no puede ser None.")

    result = np.asarray(values, dtype=float).reshape(-1)

    if result.size == 0 and not allow_empty:
        raise ValueError(f"{name} no puede estar vacío.")

    if not np.all(np.isfinite(result)):
        indexes = np.flatnonzero(~np.isfinite(result))[:10].tolist()
        raise ValueError(
            f"{name} contiene NaN o infinito en los índices {indexes}."
        )

    return result


def _optional_float(value: Any) -> Optional[float]:
    """Convierte un escalar opcional en float JSON-compatible."""
    if value is None:
        return None

    try:
        array = np.asarray(value, dtype=float).reshape(-1)
        if array.size == 0:
            return None
        result = float(array[-1])
        return result if np.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def safe_getattr(obj: Any, attribute: str) -> Any:
    try:
        return getattr(obj, attribute)
    except Exception as exc:
        return f"<ERROR leyendo {attribute}: {exc}>"


def summarize_value(value: Any, max_items: int = 8) -> Any:
    """Resume escalares, listas y arrays sin imprimir series completas."""
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
        return f"<ERROR resumiendo valor: {exc}>"


def inspect_vehicle(veh: Any) -> None:
    print("\n================ VEHICLE DEBUG ================")
    print("Tipo objeto:", type(veh))

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
            print(
                f"{attribute}: "
                f"{summarize_value(safe_getattr(veh, attribute))}"
            )

    print("================================================\n")


def inspect_simdrive(sd: Any) -> None:
    print("\n================ SIMDRIVE DEBUG ================")
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
                print(f"{attribute}: {summarize_value(value)}")
        except Exception as exc:
            print(f"{attribute}: <ERROR {exc}>")

    print("================================================\n")


def get_vehicle_id(motor_type: str) -> int:
    """Relaciona el tipo lógico con un vehículo base de FASTSim."""
    normalized = str(motor_type or "").strip().lower()
    return {
        "diesel": 9,
        "electric": 23,
        "ev": 23,
        "hybrid": 17,
    }.get(normalized, 1)


def _vehicle_motor_type(user_vehicle: VehicleModel) -> str:
    for attribute in (
        "motor_type", "engine_type", "powertrain_type", "fuel_type"
    ):
        value = getattr(user_vehicle, attribute, None)
        if value is not None:
            return str(value).strip().lower()

    return "conventional"


def convert_vehicle_to_fastsim(user_vehicle: VehicleModel):
    """Carga un powertrain coherente y sobrescribe magnitudes físicas."""
    motor_type = _vehicle_motor_type(user_vehicle)
    veh = fastsim_vehicle.Vehicle.from_vehdb(get_vehicle_id(motor_type))

    mass_kg = float(user_vehicle.total_mass)
    maximum_power_kw = float(user_vehicle.p_max_kw)
    coastdown_a_n = float(user_vehicle.A)
    coastdown_c_n_per_mps2 = float(user_vehicle.C)
    frontal_area_m2 = float(getattr(user_vehicle, "frontal_area_m2", 2.2))

    if mass_kg <= 0.0:
        raise ValueError("La masa del vehículo debe ser positiva.")
    if maximum_power_kw <= 0.0:
        raise ValueError("La potencia máxima debe ser positiva.")
    if frontal_area_m2 <= 0.0:
        raise ValueError("El área frontal debe ser positiva.")
    if coastdown_a_n < 0.0 or coastdown_c_n_per_mps2 < 0.0:
        raise ValueError("Los coeficientes A y C no pueden ser negativos.")

    veh.veh_kg = mass_kg
    veh.wheel_rr_coef = coastdown_a_n / (mass_kg * GRAVITY_M_S2)
    veh.frontal_area_m2 = frontal_area_m2
    veh.drag_coef = (
        2.0 * coastdown_c_n_per_mps2
        / (AIR_DENSITY_KG_M3 * frontal_area_m2)
    )

    # Se conserva veh_pt_type y la arquitectura del vehículo base.
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
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Devuelve longitud, velocidad y pendiente por segmento."""
    number_of_speeds = speeds.size
    distance_differences = np.diff(raw_distances)

    cumulative_boundaries = (
        raw_distances.size == number_of_speeds + 1
        and np.isclose(raw_distances[0], 0.0, atol=1e-6)
        and np.all(distance_differences >= -1e-9)
        and np.any(distance_differences > 1e-9)
    )

    if cumulative_boundaries:
        segment_lengths = distance_differences.copy()
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
            raise ValueError(
                "N distancias para N velocidades requieren un cero "
                "auxiliar en un extremo."
            )

        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
        mode = "node_speeds_one_padding_value"

    elif raw_distances.size == number_of_speeds + 1:
        # No es acumulada. Se interpreta como longitud con dos rellenos.
        segment_lengths = raw_distances[1:-1].copy()
        segment_speeds = 0.5 * (speeds[:-1] + speeds[1:])
        mode = "node_speeds_two_padding_values"

    else:
        raise ValueError(
            "Estructura espacial no reconocida: "
            f"{number_of_speeds} velocidades y "
            f"{raw_distances.size} valores de distancia."
        )

    if segment_lengths.size != segment_speeds.size:
        raise ValueError(
            "Normalización inconsistente: "
            f"{segment_lengths.size} segmentos y "
            f"{segment_speeds.size} velocidades."
        )

    if slopes_grade.size == 0:
        segment_slopes = np.zeros_like(segment_speeds)
    elif slopes_grade.size == segment_speeds.size:
        segment_slopes = slopes_grade.copy()
    elif slopes_grade.size == segment_speeds.size + 1:
        segment_slopes = 0.5 * (slopes_grade[:-1] + slopes_grade[1:])
    else:
        raise ValueError(
            "Pendientes incompatibles: "
            f"{slopes_grade.size} valores para "
            f"{segment_speeds.size} segmentos."
        )

    segment_lengths[np.isclose(segment_lengths, 0.0, atol=1e-9)] = 0.0

    if np.any(segment_lengths < 0.0):
        indexes = np.flatnonzero(segment_lengths < 0.0)[:10].tolist()
        raise ValueError(f"Longitudes negativas en {indexes}.")

    keep = segment_lengths > 0.0
    if not np.any(keep):
        raise ValueError(
            "La ruta no contiene segmentos de longitud positiva. "
            "Comprueba que SpeedProfile rellena segment_length."
        )

    return (
        segment_lengths[keep],
        segment_speeds[keep],
        segment_slopes[keep],
        mode,
    )


def _segment_to_boundaries(values: np.ndarray) -> np.ndarray:
    """Convierte N valores por segmento en N+1 valores de límite."""
    result = np.empty(values.size + 1, dtype=float)
    result[0] = values[0]
    result[-1] = values[-1]

    if values.size > 1:
        result[1:-1] = 0.5 * (values[:-1] + values[1:])

    return result


def debug_fastsim_cycle(cyc: Any) -> None:
    times = np.asarray(cyc.time_s, dtype=float)
    speeds = np.asarray(cyc.mps, dtype=float)
    duration_s = float(times[-1] - times[0])
    distance_m = float(np.trapezoid(speeds, times))

    print("\n---------- DEBUG FASTSIM CYCLE ----------")
    print(f"Puntos: {times.size}")
    print(f"Tiempo: {times[0]:.3f} .. {times[-1]:.3f} s")
    print(f"Duración: {duration_s:.3f} s")
    print(f"Distancia: {distance_m:.3f} m")
    print(f"Velocidad media: {distance_m / duration_s:.3f} m/s")
    print(f"Velocidad máxima: {np.max(speeds):.3f} m/s")
    print("-----------------------------------------\n")


class FastSimEnergyModel(VehicleEnergyModelProvider):
    """Adaptador FASTSim con conversión espacial-temporal validada."""

    def __init__(
        self,
        route: Optional[RouteModel] = None,
        vehicle: Optional[VehicleModel] = None,
    ):
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
    ):
        super().load_route_and_vehicle(route, vehicle)
        self._speed_profile = SpeedProfile(
            route=self.route,
            vehicle=self.vehicle,
        )
        self._results = None

    def _build_cycle(self):
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

        print(raw_distances)

        if speeds.size < 2:
            raise ValueError("El perfil requiere al menos dos velocidades.")

        if slopes_percent.size and np.max(np.abs(slopes_percent)) > 100.0:
            raise ValueError(
                "slope_t contiene una pendiente superior al 100 %."
            )

        # slope_t se recibe en porcentaje. FASTSim usa grade adimensional.
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

        if np.any(segment_times <= 0.0) or not np.all(
            np.isfinite(segment_times)
        ):
            raise ValueError("Se han calculado tiempos de segmento inválidos.")

        cumulative_time = np.concatenate(
            ([0.0], np.cumsum(segment_times))
        )
        total_time_s = float(cumulative_time[-1])

        boundary_speeds = _segment_to_boundaries(segment_speeds)
        boundary_slopes = _segment_to_boundaries(segment_slopes)

        if not np.isfinite(self.dt) or self.dt <= 0.0:
            raise ValueError(f"self.dt debe ser positivo: {self.dt}.")

        times = np.arange(0.0, total_time_s, self.dt, dtype=float)
        if times.size == 0 or not np.isclose(times[-1], total_time_s):
            times = np.append(times, total_time_s)

        speed_mps = np.interp(
            times,
            cumulative_time,
            boundary_speeds,
        )
        slope_series = np.interp(
            times,
            cumulative_time,
            boundary_slopes,
        )
        road_type = np.zeros(times.size, dtype=int)

        cyc = cycle.Cycle(
            times,
            speed_mps,
            slope_series,
            road_type,
            "custom_cycle",
        )

        self._validate_cycle(cyc, expected_distance_m)

        if self.debug:
            print(f"Modo espacial: {spatial_mode}")
            print(
                "Pendiente original: "
                f"{np.min(slopes_percent, initial=0.0):.3f} % .. "
                f"{np.max(slopes_percent, initial=0.0):.3f} %"
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
            raise ValueError(
                "El ciclo necesita tiempo y velocidad de igual longitud."
            )

        if np.any(np.diff(times) <= 0.0):
            raise ValueError("El tiempo no es estrictamente creciente.")

        simulated_distance_m = float(np.trapezoid(speeds, times))
        error_fraction = (
            simulated_distance_m - expected_distance_m
        ) / expected_distance_m

        if abs(error_fraction) > max_error_fraction:
            raise ValueError(
                "El remuestreo no conserva la distancia: "
                f"esperada={expected_distance_m:.3f} m, "
                f"simulada={simulated_distance_m:.3f} m, "
                f"error={100.0 * error_fraction:.3f} %."
            )

    def perform_speed_profile_processing(self):
        self._speed_profile.calculate_acceleration()
        self._speed_profile.calculate_resistances()
        self._speed_profile.calculate_gravitational_resistances()

    def perform_speed_profile_estimation(self):
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

    def retrieve_estimations(self):
        return self._results

    @staticmethod
    def _cycle(sd: Any):
        cyc = getattr(sd, "cyc", None)
        if cyc is None:
            cyc = getattr(sd, "cyc0", None)
        if cyc is None:
            raise ValueError("SimDrive no contiene cyc ni cyc0.")
        return cyc

    @classmethod
    def _distance_m(cls, sd: Any) -> float:
        """Prioriza la velocidad conseguida para detectar trace miss."""
        cyc = cls._cycle(sd)

        if hasattr(sd, "mps_ach") and hasattr(cyc, "time_s"):
            return float(
                np.trapezoid(
                    np.asarray(sd.mps_ach, dtype=float),
                    np.asarray(cyc.time_s, dtype=float),
                )
            )

        if hasattr(sd, "dist_mi"):
            return float(
                np.sum(np.asarray(sd.dist_mi, dtype=float))
                * METERS_PER_MILE
            )

        if hasattr(sd, "dist_m"):
            return float(np.sum(np.asarray(sd.dist_m, dtype=float)))

        if hasattr(cyc, "mps") and hasattr(cyc, "time_s"):
            return float(np.trapezoid(cyc.mps, cyc.time_s))

        raise ValueError("No se puede obtener la distancia de SimDrive.")

    @staticmethod
    def _fuel_energy_kwh(sd: Any) -> Optional[float]:
        if hasattr(sd, "fs_kwh_out_ach"):
            return float(
                np.sum(np.asarray(sd.fs_kwh_out_ach, dtype=float))
            )

        if hasattr(sd, "fuel_kj"):
            return float(sd.fuel_kj) / 3600.0

        if hasattr(sd, "fs_cumu_mj_out_ach"):
            values = np.asarray(sd.fs_cumu_mj_out_ach, dtype=float)
            return float(values[-1]) / 3.6 if values.size else None

        return None

    @staticmethod
    def _battery_energy_kwh(sd: Any) -> Optional[float]:
        for attribute in (
            "ess_kwh_out_ach",
            "battery_kwh_out_ach",
        ):
            if hasattr(sd, attribute):
                return float(
                    np.sum(np.asarray(getattr(sd, attribute), dtype=float))
                )

        return None

    def extract_consumption_summary(self, sd: Any) -> Dict[str, Any]:
        """Extrae resultados con unidades y frontera energética explícitas."""
        cyc = self._cycle(sd)
        times = _array(cyc.time_s, "cyc.time_s")

        if times.size < 2:
            raise ValueError("El ciclo debe contener al menos dos tiempos.")

        time_differences = np.diff(times)
        if np.any(time_differences <= 0.0):
            raise ValueError("El tiempo del ciclo no es creciente.")

        time_s = float(times[-1] - times[0])
        distance_m = self._distance_m(sd)
        distance_km = distance_m / 1000.0
        time_h = time_s / 3600.0

        if distance_km <= 0.0:
            raise ValueError(f"Distancia FASTSim inválida: {distance_m} m.")
        if time_h <= 0.0:
            raise ValueError(f"Tiempo FASTSim inválido: {time_s} s.")

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
                raise ValueError(
                    "No se encontró energía de batería en SimDrive. "
                    "Activa debug para inspeccionar los atributos ESS."
                )

            energy_source = "battery"
            energy_boundary = "battery_output"
            energy_consumption = float(energy_kwh)
            consumption_unit = "kWh"
            total_liters_equivalent = None
            liters_equivalent_per_100_km = None

        else:
            energy_kwh = self._fuel_energy_kwh(sd)

            if energy_kwh is None:
                raise ValueError(
                    "No se encontró energía de combustible en SimDrive."
                )

            total_liters_equivalent = (
                float(energy_kwh)
                / KWH_PER_GGE
                * LITERS_PER_GALLON
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
            raise ValueError(
                f"Energía FASTSim inválida: {energy_kwh} kWh."
            )

        avg_speed_kmh = distance_km / time_h
        kwh_per_100_km = energy_kwh / distance_km * 100.0
        wh_per_km = energy_kwh * 1000.0 / distance_km
        distance_time_ratio = distance_m / time_s

        # Si metros y segundos son casi iguales, puede haberse usado la
        # distancia acumulada como eje temporal.
        possible_distance_as_time = bool(
            distance_m > 100.0
            and abs(time_s - distance_m) / distance_m < 0.02
        )

        result: Dict[str, Any] = {
            # Consumo total del trayecto.
            "energyConsumption": float(energy_consumption),
            "energyConsumptionUnit": consumption_unit,

            # Energía total de la fuente durante la simulación.
            "energyKwh": energy_kwh,
            "energyUnit": "kWh",
            "energySource": energy_source,
            "energyBoundary": energy_boundary,

            # Misma unidad principal que GRETA.
            "distance": float(distance_m),
            "distanceUnit": "m",
            "distanceKm": float(distance_km),

            # Tiempo real del ciclo.
            "time": float(time_s),
            "timeUnit": "s",

            # Métricas derivadas.
            "avgSpeedKmh": float(avg_speed_kmh),
            "kwhPer100Km": float(kwh_per_100_km),
            "whPerKm": float(wh_per_km),

            # Seguimiento del ciclo.
            "traceMiss": _optional_float(
                getattr(sd, "trace_miss", None)
            ),
            "traceMissDistanceFraction": _optional_float(
                getattr(sd, "trace_miss_dist_frac", None)
            ),

            # Diagnóstico temporal y dimensional.
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
                    "fuelLiters": float(
                        total_liters_equivalent
                    ),
                    "fuelLitersPer100Km": float(
                        liters_equivalent_per_100_km
                    ),
                    "fuelEnergyKwhPer100Km": float(kwh_per_100_km),
                    "batteryEnergyKwh": None,
                    "batteryKwhPer100Km": None,
                    "batteryWhPerKm": None,
                }
            )

        return result

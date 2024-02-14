from route_consumption_estimator.vehicle.constants import GRAVITY, CX, RO, POWER_PERCENTAGE, \
    ENGINE_PERFORMANCE, ACC_LIMIT_PROPORTION


class VehicleModel:
    """
    Vehicle model information
    """

    def __init__(self, total_veh_mass: int, p_max_kw: float, avg_consumption: float,
                 A: float, B: float, C: float, motor_type: str, gamma: float = 1.05,  auxiliar_consumption_l_h: float = 0):

        self._total_mass = total_veh_mass

        self._gamma = gamma  # Majority factor of rotating masses

        self._motor_type = motor_type

        self._avg_consumption = avg_consumption

        self._A = A
        self._B = B
        self._C = C

        # If other more precise values are available, they can be entered directly for the calculation of the
        # resistances. passive, be careful with the units, as they are usually expressed for a speed in km/h and not
        # in m/s.

        # Definition of driving criteria. Three driving ranges are established
        self._v1_km_h = 50  # First speed limit in km/h
        self._v2_km_h = 100  # Second speed limit in km/h

        # Define acceleration limit proportion
        self._acc_limit_proportion = ACC_LIMIT_PROPORTION

        self._ax_trac1 = 2  # Maximum longitudinal tensile acceleration in m/s^2 with speed less than v1_km_h
        self._ax_trac2 = 1  # Maximum longitudinal tensile acceleration in m/s^2 with speed between v1_km_h and v2_km_h
        self._ax_trac3 = 0.5  # Maximum longitudinal tensile acceleration in m/s^2 with velocity greater than v2_km_h

        self._ax_brake = -2  # Longitudinal braking acceleration in m/s^2

        # Definition of engine variables
        self._p_max_kw = p_max_kw  # Maximum engine power in kW

        self._power_percentage = POWER_PERCENTAGE  # Percentage value of maximum power for performance calculation

        self._engine_performance = ENGINE_PERFORMANCE  # Performance value

        self._auxiliar_consumption_l_h = auxiliar_consumption_l_h  # Consumption auxiliary equipment


    @property
    def total_mass(self):
        """Get the value of total_mass."""
        return self._total_mass

    @total_mass.setter
    def total_mass(self, value):
        """Set the value of total_mass."""
        self._total_mass = value

    @property
    def gamma(self):
        """Get the value of gamma."""
        return self._gamma

    @gamma.setter
    def gamma(self, value):
        """Set the value of gamma."""
        self._gamma = value

    @property
    def A(self):
        """Get the value of A."""
        return self._A

    @A.setter
    def A(self, value):
        """Set the value of A."""
        self._A = value

    @property
    def B(self):
        """Get the value of B."""
        return self._B

    @B.setter
    def B(self, value):
        """Set the value of B."""
        self._B = value

    @property
    def C(self):
        """Get the value of C."""
        return self._C

    @C.setter
    def C(self, value):
        """Set the value of C."""
        self._C = value

    @property
    def v1_km_h(self):
        """Get the value of v1_km_h."""
        return self._v1_km_h

    @v1_km_h.setter
    def v1_km_h(self, value):
        """Set the value of v1_km_h."""
        self._v1_km_h = value

    @property
    def v2_km_h(self):
        """Get the value of v2_km_h."""
        return self._v2_km_h

    @v2_km_h.setter
    def v2_km_h(self, value):
        """Set the value of v2_km_h."""
        self._v2_km_h = value

    @property
    def ax_trac1(self):
        """Get the value of ax_trac1."""
        return self._ax_trac1

    @ax_trac1.setter
    def ax_trac1(self, value):
        """Set the value of ax_trac1."""
        self._ax_trac1 = value

    @property
    def ax_trac2(self):
        """Get the value of ax_trac2."""
        return self._ax_trac2

    @ax_trac2.setter
    def ax_trac2(self, value):
        """Set the value of ax_trac2."""
        self._ax_trac2 = value

    @property
    def ax_trac3(self):
        """Get the value of ax_trac3."""
        return self._ax_trac3

    @ax_trac3.setter
    def ax_trac3(self, value):
        """Set the value of ax_trac3."""
        self._ax_trac3 = value

    @property
    def ax_brake(self):
        """Get the value of ax_brake."""
        return self._ax_brake

    @ax_brake.setter
    def ax_brake(self, value):
        """Set the value of ax_brake."""
        self._ax_brake = value

    @property
    def p_max_kw(self):
        """Get the value of p_max_kw."""
        return self._p_max_kw

    @p_max_kw.setter
    def p_max_kw(self, value):
        """Set the value of p_max_kw."""
        self._p_max_kw = value

    @property
    def avg_consumption(self):
        """Get the value of avg_consumption."""
        return self._avg_consumption

    @avg_consumption.setter
    def avg_consumption(self, value):
        """Set the value of avg_consumption."""
        self._avg_consumption = value

    @property
    def power_percentage(self):
        """Get the value of power_percentage."""
        return self._power_percentage

    @power_percentage.setter
    def power_percentage(self, value):
        """Set the value of power_percentage."""
        self._power_percentage = value

    @property
    def engine_performance(self):
        """Get the value of engine_performance."""
        return self._engine_performance

    @engine_performance.setter
    def engine_performance(self, value):
        """Set the value of engine_performance."""
        self._engine_performance = value

    @property
    def motor_type(self):
        """Get the value of motor_type."""
        return self._motor_type

    @motor_type.setter
    def motor_type(self, value):
        """Set the value of motor_type."""
        self._motor_type= value

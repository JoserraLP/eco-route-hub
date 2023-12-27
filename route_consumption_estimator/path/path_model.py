class PathModel:
    """
    In this part, the data that make up the path to be analyzed are entered.
    The path is defined by a succession of sections. Each section is defined by the following matrices:

    **segment_start_point**: Variable indicating the starting point of each leg, measured in meters from the origin.

    **speed_limit_km_h**: Speed limit of each leg, expressed in km/h.

    **Slope**: Slope of the section, expressed in sexagesimal degrees.
    """

    def __init__(self, segment_start_point: list, speed_limit_km_h: list, slope: list):
        # The path definition is characterized by the distance to the origin of the start of each segment, measured
        # in meters (m).

        self._segment_start_point = segment_start_point  # Vector of the start of the segment

        self._total_distance = max(segment_start_point)  # Total length of the route

        #  Speed limit on each section, obtained from the maximum speed of the section, modified by the state of the
        #  traffic. It is expressed in km/h

        # Segment speed limits
        self._speed_limit_km_h = speed_limit_km_h

        # Ramp of each segment expressed in %. It is considered that the %
        # ramp(%)=100*tan(inclination)=100*sin(inclination)

        # Slope of each segment
        self._slope = slope

    @property
    def segment_start_point(self):
        """Get the value of segment_start_point."""
        return self._segment_start_point

    @segment_start_point.setter
    def segment_start_point(self, value):
        """Set the value of segment_start_point."""
        self._segment_start_point = value

    @property
    def total_distance(self):
        """Get the value of total_distance."""
        return self._total_distance

    @total_distance.setter
    def total_distance(self, value):
        """Set the value of total_distance."""
        self._total_distance = value

    @property
    def speed_limit_km_h(self):
        """Get the value of speed_limit_km_h."""
        return self._speed_limit_km_h

    @speed_limit_km_h.setter
    def speed_limit_km_h(self, value):
        """Set the value of speed_limit_km_h."""
        self._speed_limit_km_h = value

    @property
    def slope(self):
        """Get the value of slope."""
        return self._slope

    @slope.setter
    def slope(self, value):
        """Set the value of slope."""
        self._slope = value

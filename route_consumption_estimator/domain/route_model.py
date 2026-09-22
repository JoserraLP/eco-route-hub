class RouteModel:
    """
    In this part, the data that make up the path to be analyzed are entered.
    The path is defined by a succession of sections. Each section is defined by the following matrices:

    **segment_start_point**: Variable indicating the starting point of each leg, measured in meters from the origin.

    **additional_information**: dict with additional route information
    """

    def __init__(self, segment_start_point: list, additional_info: dict):
        # The path definition is characterized by the distance to the origin of the start of each segment, measured
        # in meters (m).
        self._segment_start_point = segment_start_point  # Vector of the start of the segment

        self._total_distance = max(segment_start_point)  # Total length of the route

        self._additional_info = additional_info

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
    def additional_info(self):
        """Get the value of additional_info."""
        return self._additional_info

    @additional_info.setter
    def additional_info(self, value):
        """Set the value of additional_info."""
        self._additional_info = value

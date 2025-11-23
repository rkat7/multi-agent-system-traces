    def _value_in_bounds(self, vals):
        """Clip min, max values to the bounds."""
        return (self._min_in_bounds(vals[0]), self._max_in_bounds(vals[1]))

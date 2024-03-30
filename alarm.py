
    

class Alarm:
    def __init__(self):
        self._time = {"hour": 0, "minute": 0}
        self._enabled = False
    
    @property
    def hour(self):
        return self._time["hour"]
    
    @hour.setter
    def hour(self, new_hour):
        self._time["hour"] = new_hour
    
    @property
    def minute(self):
        return self._time["minute"]
    
    @minute.setter
    def minute(self, new_minute):
        self._time["minute"] = new_minute
    
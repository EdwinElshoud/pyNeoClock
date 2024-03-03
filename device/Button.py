from machine import Pin
import time

class Button(object):
    
    rest_state = False
    # pin = None
    # pin_number = 0
    RELEASED = 'released'
    PRESSED = 'pressed'
    LONGPRESS = 'longpress'
    LONGPRESS_REPEAT = 'longpress_repeat'
    LONGPRESS_RELEASED = 'longpress_released'
    
    def __init__(self, pin, rest_state = False, callback = None, internal_pullup = False, internal_pulldown = False):
        self.pin_number = pin
        self.rest_state = rest_state
        if internal_pulldown:
            self.internal_pull = Pin.PULL_DOWN
            self.rest_state = False
        elif internal_pullup:
            self.internal_pull = Pin.PULL_UP
            self.rest_state = True
        else:
            self.internal_pull = None
        
        self.pin = Pin(pin, mode = Pin.IN, pull = self.internal_pull)
        
        self.callback = callback
        self.active = False
        self.last_event_time = None
        self._is_longpress = False
        
    def _is_repeat_time(self, interval):
        """
        Check if the repeat event has elapsed.
        """
        if self._last_event_time is None:
            self._last_event_time = time.ticks_ms()
            return False
        
        if (time.ticks_ms() - self._last_event_time) > interval:
            # restart the timer
            self._last_event_time = time.ticks_ms()
            return True
        
        return False
    
    def update(self, repeat_interval):
        
        if self.pin.value() == (not self.rest_state):
            if not self.active:
                self.active = True
                do_callback = True
                self._last_event_time = time.ticks_ms()
                if self.callback:
                    self.callback(self.pin_number, Button.PRESSED)
            else:
                if self._is_repeat_time(repeat_interval) and self.callback:
                    # Check for repeat interval to do the callback again (and again...)
                    if self._is_longpress == False:
                        self.callback(self.pin_number, Button.LONGPRESS)
                        self._is_longpress = True
                    else:
                        self.callback(self.pin_number, Button.LONGPRESS_REPEAT)
                
            return
        
        if self.pin.value() == self.rest_state and self.active:
            self.active = False
            if self.callback != None:
                if self._is_longpress:
                    self.callback(self.pin_number, Button.LONGPRESS_RELEASED)
                else:
                    self.callback(self.pin_number, Button.RELEASED)
                self._is_longpress = False
            return
    
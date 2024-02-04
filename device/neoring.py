OFFSET=20

class NeoRing:
    def __init__(self, neo, num_pixels):
        self._num_pixels = num_pixels
        self._neo = neo   # create NeoPixel driver on GPIO33 for N pixels

    def off(self):
        for pixel in range(0, self._num_pixels):
            #display_tm1637.number(pixel)
            self._neo[pixel] = (0,0,0)   # set the first pixel to white
            self._neo.write()              # write data to all pixels
        
    def light(self, color, brightness):
        """
        Set all pixels on.
        
        :param color: tuple (r, g, b)
        :param brightness: 0 .. 1.0
        """
        r = float(color[0]) * brightness
        g = float(color[1]) * brightness
        b = float(color[2]) * brightness
        r = int(r)
        g = int(g)
        b = int (b)
        for pixel in range(0, self._num_pixels):
            #display_tm1637.number(pixel)
            self._neo[pixel] = (r,g,b)   # set the first pixel to white
            self._neo.write()              # write data to all pixels

    def clear(self, clear_color=(0,0,0), with_write=False):
        
        for pixel in range(0, self._num_pixels):
            #display_tm1637.number(pixel)
            self._neo[pixel] = clear_color   # set the first pixel to white
            
        if with_write:
            self._neo.write()              # write data to all pixels
        
    
    def show_time(self, hour, minute):
        led_hour = int((hour * (self._num_pixels)) / 12)
        led_minute = int((minute * (self._num_pixels)) / 60)
        led_hour = (led_hour + OFFSET) % self._num_pixels
        led_minute = (led_minute + OFFSET) % self._num_pixels
        print(f'Hour idx: {led_hour}')
        print(f'Minute idx: {led_minute}')
        color_hour = (64,0,0)
        color_minute = (0,0,64)
        self.clear()
        self._neo[led_hour] = color_hour
        self._neo[led_minute] = color_minute
        self._neo.write()
    
    
        
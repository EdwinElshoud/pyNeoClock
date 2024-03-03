import machine
import time

class Mp3Player:
    
  NEXT=0x01
  PREVIOUS=0x02
  PLAY_TRACK=0x03
  VOLUME_UP=0x04
  VOLUME_DOWN=0x05
  SET_VOLUME=0x06
  SET_EQUALIZER=0x07
  SET_PLAY_MODE=0x08
  SET_PLAY_SOURCE=0x09
  SET_STDBY=0x0A
  RESET=0x0C
  PLAY=0x0D
  PAUSE=0x0E
  PLAY_FOLDER=0x0F
  SET_REPEAT_PLAY=0x11
  STOP=0x16
  GET_CURRENT_STATUS=0x42
  GET_CURRENT_TRACK=0x4B

  COM_START = 0x7E
  COM_END = 0xEF
  COM_VERSION = 0xFF
  
  PLAYBACK_MODE_REPEAT = 0x00
  PLAYBACK_MODE_REPEAT_FOLDER = 0x01
  PLAYBACK_MODE_REPEAT_SINGLE = 0x02
  PLAYBACK_MODE_RANDOM = 0x03
  
  def __init__(self, uart_id, tx_pin, rx_pin):
    self._uart_id = uart_id
    self._uart = machine.UART(uart_id, 9600)
    
    if tx_pin and rx_pin:
      self._uart.init(9600, bits=8, parity=None, stop=1, tx=tx_pin, rx=rx_pin)
    else:
      self._uart.init(9600, bits=8, parity=None, stop=1)
      
    self._uart.flush()
    self._is_playing = False
    

  def _checksum(self, msg):
    checksum = 0
    for d in msg:
      checksum = checksum + d
    checksum_bytes = bytearray(2)
    checksum_bytes[0] = (checksum>>7) - 1
    checksum_bytes[0] = ~checksum_bytes[0]
    checksum_bytes[1] = checksum - 1
    checksum_bytes[1] = ~checksum_bytes[1]
    return checksum_bytes
    
  def _send(self, cmd, payload, need_reply=False):
    # Add 3 for version, command and reply 
    msg = bytearray([self.COM_START,])

    data_length = len(payload) + 4
    reply_field = 0x01 if need_reply else 0x00
    header = bytearray([self.COM_VERSION, data_length, cmd, reply_field])
    
    msg.extend(header)
    msg.extend(payload)
    msg.extend(self._checksum(msg[1:]))
    msg.extend(bytearray([self.COM_END,]))
    
    print("Sending message:")
    print(msg)
    self._uart.write(msg)
    
  def _receive(self):
    in_bytes = self._uart.read()
    return in_bytes

  def reset(self):
    self._send(self.RESET, payload=bytearray([0, 1]))
  
  def stop(self):
    self._send(self.STOP, payload=bytearray([0, 0]))
    self._is_playing = False
    
  def play(self):
    self._send(self.PLAY_FOLDER, payload=bytearray([1, 2])) 
    self._is_playing = True

  def play_next(self):
    self._send(self.NEXT, payload=bytearray([0, 0]))
    self._is_playing = True
    
  def play_previous(self):
    self._send(self.PREVIOUS, payload=bytearray([0, 0]))
    self._is_playing = True

  def play_random(self):
    self._send(0x18, payload=bytearray([0, 0]))
    self._is_playing = True

  def set_playback_mode(self, pb_mode):
    self._send(self.SET_PLAY_MODE, payload=bytearray([0, pb_mode]))
    self._is_playing = True
    
  def set_volume(self, level):
    self._send(self.SET_VOLUME, payload=bytearray([0, level]))

  def volume_up(self):
    self._send(self.VOLUME_UP, payload=bytearray([0, 0]))

  def volume_down(self):
    self._send(self.VOLUME_DOWN, payload=bytearray([0, 0]))

  def get_status(self):
    self._uart.flush()
    self._send(self.GET_CURRENT_STATUS, payload=bytearray([0, 0]))
    result = self._receive()
    print(result)
    
  def is_playing(self):
    return self._is_playing
    
if __name__ == "__main__":
    mp3player = Mp3Player(1,17,16)
    #mp3player.reset()
    time.sleep(2)
    mp3player.set_playback_mode(Mp3Player.PLAYBACK_MODE_RANDOM)
    time.sleep(0.5)
    #mp3player.play()
    #print(mp3player.get_status())
    mp3player.set_volume(5)
    time.sleep(0.5)
    
    mp3player.get_status()
    time.sleep(10)
    mp3player.stop()
  

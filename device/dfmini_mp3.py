

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
  PLAY=0x0D
  PAUSE=0x0E
  PLAY_FOLDER=0x0F
  SET_REPEAT_PLAY=0x11
  STOP=0x16
  GET_CURRENT_STATUS=0x42
  GET_CURRENT_TRACK=0x4B

  COM_START = 0xFE
  COM_END = 0xEF
  COM_VERSION = 0xFF
  
  def __init__(self, uart_id):
    self._uart_id = uart_id
    self._uart = machine.UART(uart_id, 9600)
    self._uart.flush()
    

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
    
  def _send(self, cmd, payload, need_reply):
    # Add 3 for version, command and reply 
    data_length = len(payload) + 2
    reply_field = 0x01 if need_reply else 0x00
    header = bytes(self.COM_VERSION, data_length, cmd, reply_field)
    data = b''.join([header,payload])
    msg = b''.join([self.COM_START, data, _checksum(data), self.COM_END)
    self._uart.write(msg)

  def stop(self):
    self._send(self.STOP, payload=bytearray([0,0]), need_reply=False)
    
  def play(self):
    self._send(self.PLAY, payload=bytearray([0,0]), need_reply=False) 

  

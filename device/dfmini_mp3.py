

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
  GET_CURRENT_STATUS=0x42
  GET_CURRENT_TRACK=0x4B
  
  def __init__(self):
    pass

  def _send(self, cmd, payload, need_reply):
    # Add 2 for command and reply 
    data_length = len(payload) + 2
    reply_field = 0x01 if need_reply else 0x00
    header = bytes(0x7E, 0xFF, data_length, cmd, reply_field)
    data=b''.join( blokhaken.... header,payload)


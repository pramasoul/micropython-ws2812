# Mock standin for pyb, for running under unix or Cpython

import random
import sys
import time

def millis():
    return int(time.time() * 1000) & 0x7fffffff

def elapsed_millis(t0):
    return (int(time.time() * 1000) - t0) & 0x7fffffff

def micros():
    return int(time.time() * 1000000) & 0x7fffffff

def elapsed_micros(t0):
    return (int(time.time() * 1000000) - t0) & 0x7fffffff

def info():
    print("I'm a dummy.")

def rng():
    return random.getrandbits(30)

def wfi():
    #time.sleep((999 - (micros() % 1000))/1000)
    #print('.', end='')
    return

# utility methods
def _little_endian_bytes(v):
    t = v
    n = 0
    while (t):
        t >>= 8
        n += 1
    n = max(n, 1)
    return bytes((v >> 8*i) & 0xff for i in range(n))
    
def _time_as_8_bytes():
    t = int(time.time() * 1000000)
    return bytes((t >> 8*i) & 0xff for i in range(8))

def _big_endian_int(b):
    rv = 0
    for v in list(b):
        rv = (rv << 8) + int(v)
    return rv

def _little_endian_int(b):
    rv = 0
    o = 0
    for v in list(b):
        rv += int(v) << o
        o += 8
    return rv


# Dummy hardware:

class LED:

    def __init__(self, index):
        self.index = index
        self.state = None

    def on(self):
        self.state = True

    def off(self):
        self.state = False

    def get(self):
        return self.state

    def toggle(self):
        v = self.get()
        if v:
            self.off()
        else:
            self.on()


class Pin:
    def __init__(self, name):
        self.name = name

class ADC:
    def __init__(self, pin):
        self.pin = pin

    def read(self):
        return 2047


class SPI:
    MASTER = 'master'
    SLAVE = 'slave'
    LSB = 'lsb'
    MSB = 'msb'
    def __init__(self, bus, *args, **kwargs):
        self.bus = bus
        self.recording_file = None

    def send(self, data, *args, **kwargs):
        f = self.recording_file
        if f:
            t = _time_as_8_bytes()
            #assert len(t) == 8, 'time as bytes is not 8 bytes long'
            #print(len(t), len(data))
            buf = bytearray(2)
            n = len(t) + len(data)
            buf[0] = n & 0xff
            buf[1] = (n >> 8) & 0xff
            f.write(buf)
            f.write(t)
            f.write(data)
            #f.flush()
            
"""
STATIC const mp_map_elem_t pyb_spi_locals_dict_table[] = {
    // instance methods
    { MP_OBJ_NEW_QSTR(MP_QSTR_init), (mp_obj_t)&pyb_spi_init_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_deinit), (mp_obj_t)&pyb_spi_deinit_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_send), (mp_obj_t)&pyb_spi_send_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_recv), (mp_obj_t)&pyb_spi_recv_obj },
    { MP_OBJ_NEW_QSTR(MP_QSTR_send_recv), (mp_obj_t)&pyb_spi_send_recv_obj },

    // class constants
    /// \constant MASTER - for initialising the bus to master mode
    /// \constant SLAVE - for initialising the bus to slave mode
    /// \constant MSB - set the first bit to MSB
    /// \constant LSB - set the first bit to LSB
    { MP_OBJ_NEW_QSTR(MP_QSTR_MASTER), MP_OBJ_NEW_SMALL_INT(SPI_MODE_MASTER) },
    { MP_OBJ_NEW_QSTR(MP_QSTR_SLAVE),  MP_OBJ_NEW_SMALL_INT(SPI_MODE_SLAVE) },
    { MP_OBJ_NEW_QSTR(MP_QSTR_MSB),    MP_OBJ_NEW_SMALL_INT(SPI_FIRSTBIT_MSB) },
    { MP_OBJ_NEW_QSTR(MP_QSTR_LSB),    MP_OBJ_NEW_SMALL_INT(SPI_FIRSTBIT_LSB) },
    /* TODO
    { MP_OBJ_NEW_QSTR(MP_QSTR_DIRECTION_2LINES             ((uint32_t)0x00000000)
    { MP_OBJ_NEW_QSTR(MP_QSTR_DIRECTION_2LINES_RXONLY      SPI_CR1_RXONLY
    { MP_OBJ_NEW_QSTR(MP_QSTR_DIRECTION_1LINE              SPI_CR1_BIDIMODE
    { MP_OBJ_NEW_QSTR(MP_QSTR_NSS_SOFT                    SPI_CR1_SSM
    { MP_OBJ_NEW_QSTR(MP_QSTR_NSS_HARD_INPUT              ((uint32_t)0x00000000)
    { MP_OBJ_NEW_QSTR(MP_QSTR_NSS_HARD_OUTPUT             ((uint32_t)0x00040000)
    */
};
"""

class Timer:
    def __init__(self):
        pass

class USB_VCP:
    def __init__(self):
        self.inf = sys.stdin
        self.outf = sys.stdout
        self.buf = b''
        self.write = self.outf.write

    def isconnected(self):
        return True

    def read(self, size=None):
        if size is None:
            return self.readall()
        if size < 0:
            return b''
        while len(self.buf) < self.size:
            self.buf += self.inf.read(size - len(self.buf))
        rv =self.buf[:size]
        self.buf = self.buf[size:]
        return rv

    def any(self):
        return False            # FIXME

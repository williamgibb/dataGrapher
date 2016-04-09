"""
Default serial port configuration settings for devices

These dictionaries are designed to be dropped into the pyserial serial.Serial()
object init via a **kwargs style object creation.
"""
"""
baudrate=9600, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE, timeout=None, xonxoff=False, rtscts=False, write_timeout=None
"""
import serial

# Mettler-Toledo NewClassic Balances
# MS-S / MS-L Models
MT_NCLASSIC_DEFAULT = {
    'baudrate': 9600,
    'bytesize': serial.EIGHTBITS,
    'parity': serial.PARITY_NONE,
    'stopbits': serial.STOPBITS_ONE,
    'xonxoff': True,
    'timeout': 60
}
"""
Default serial port configuration settings for devices

These dictionaries are designed to be dropped into the pyserial serial.Serial()
object init via a **kwargs style object creation.
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

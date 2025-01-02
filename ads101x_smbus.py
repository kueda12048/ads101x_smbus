"""
 Description: A Python library for the ADS1015 ADC using the smbus library.
 https://www.ti.com/product/ja-jp/ADS1015
"""

from smbus import SMBus
from typing import NoReturn
import time

_RET_CONVERSION = 0x00
_REG_ADC_CONFIG = 0x01
_REG_LO_THRESH = 0x02
_REG_HI_THRESH = 0x03

class Mux:
    """
    The input multiplexer configuration.
    """
    AIN0_AIN1 = 0x0 # Differential P = AIN0, N = AIN1 (default)
    AIN0_AIN3 = 0x1 # Differential P = AIN0, N = AIN3
    AIN1_AIN3 = 0x2 # Differential P = AIN1, N = AIN3
    AIN2_AIN3 = 0x3 # Differential P = AIN2, N = AIN3
    AIN0_GND = 0x4  # Single-ended P = AIN0, N = GND
    AIN1_GND = 0x5  # Single-ended P = AIN1, N = GND
    AIN2_GND = 0x6  # Single-ended P = AIN2, N = GND
    AIN3_GND = 0x7  # Single-ended P = AIN3, N = GND

class Gain:
    """
    The gain of the ADC.
    """
    TWOTHIRDS = 0x0000  # +/- 6.144V
    ONE = 0x0200        # +/- 4.096V
    TWO = 0x0400        # +/- 2.048V (default)
    FOUR = 0x0600       # +/- 1.024V
    EIGHT = 0x0800      # +/- 0.512V
    SIXTEEN = 0x0A00    # +/- 0.256V

class DataRate:
    """
    The data rate of the ADC.
    """
    SPS_128 = 0x0000    # 128 samples per second
    SPS_250 = 0x0020    # 250 samples per second
    SPS_490 = 0x0040    # 490 samples per second
    SPS_920 = 0x0060    # 920 samples per second
    SPS_1600 = 0x0080   # 1600 samples per second (default)
    SPS_2400 = 0x00A0   # 2400 samples per second
    SPS_3300 = 0x00C0   # 3300 samples per second

class RWBits:
    """
    :param int num_bits: The number of bits in the field.
    :param int register_address: The register address to read the bit from
    :param int lowest_bit: The lowest bits index within the byte at ``register_address``
    :param int register_width: The number of bytes in the register.
    :param bool signed: Handling negative values.
    """
    def __init__(self, num_bits: int, register_address: int, lowest_bit: int, register_width: int, signed: bool = False) -> None:
        self.bit_mask = ( (1<<num_bits) -1 ) << lowest_bit
        if self.bit_mask >= 1 << (register_width * 8):
            raise ValueError("Cannot have more bits than register size")
        self.num_bits = num_bits
        self.register_address = register_address
        self.register_width = register_width
        self.lowest_bit = lowest_bit
        self.signed = signed

    def __get__(self, obj, objtype) -> int:
        read_data = obj.i2c.read_i2c_block_data(obj.address, self.register_address, self.register_width)
        val = 0
        for i, data in enumerate(read_data):
            val += data << (self.register_width-1-i)*8
        val = (val & self.bit_mask) >> self.lowest_bit

        if not self.signed:
            return val
        if val & (1 << (self.num_bits-1) ): # true : negative
            # print(val)
            # print(((1<<self.num_bits)-1))
            val = -( ( ~val&((1<<self.num_bits)-1) ) + 1 )
        return val

    def __set__(self, obj, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("value must be an integer")
        read_data = obj.i2c.read_i2c_block_data(obj.address, self.register_address, self.register_width)
        # print(read_data)
        val = 0
        for i, data in enumerate(read_data):
            val += data << (self.register_width-1-i)*8
        val &= (~self.bit_mask & ( (1<<self.register_width*8) -1 ) ) # Set the target bit to 0
        val |= (value << self.lowest_bit)
        send_data = []
        for i in range(self.register_width):
            send_data.append( (val>>( (self.register_width-1-i)*8 )) & 0xFF )
        # print(send_data)
        obj.i2c.write_i2c_block_data(obj.address, self.register_address, send_data)

class ROBits(RWBits):
    """
    Read-only bits.
    """
    def __set__(self, obj, value: int) -> NoReturn:
        raise AttributeError()

class ADS101X_SMBus:

    operation_status = RWBits(1, _REG_ADC_CONFIG, 15, 2)
    """ The operational status of the ADC. 0: Not operational, 1: Operational. """
    mux_reg = RWBits(3, _REG_ADC_CONFIG, 12, 2)
    """ The input multiplexer configuration. """
    pga_reg = RWBits(3, _REG_ADC_CONFIG, 9, 2)
    """ The programmable gain amplifier configuration. """
    mode_reg = RWBits(1, _REG_ADC_CONFIG, 8, 2)
    """ The operating mode of the ADC. 0: Continuous, 1: Single-shot. """
    data_rate = RWBits(3, _REG_ADC_CONFIG, 5, 2)
    """ The data rate of the ADC. """
    comparator_mode = RWBits(1, _REG_ADC_CONFIG, 4, 2)
    """ The comparator mode of the ADC. 0: Traditional, 1: Window. """
    comparator_polarity = RWBits(1, _REG_ADC_CONFIG, 3, 2)
    """ The polarity of the comparator. 0: Active low, 1: Active high. """
    comparator_latching = RWBits(1, _REG_ADC_CONFIG, 2, 2)
    """ The latching mode of the comparator. 0: Non-latching, 1: Latching. """
    comparator_queue = RWBits(2, _REG_ADC_CONFIG, 0, 2)
    """ The number of comparator conversions before asserting the alert pin. """

    conversion_result = ROBits(12, _RET_CONVERSION, 4, 2, signed=True)
    """ The last conversion result. """

    def __init__(self, bus_number: int, address: int = 0x48) -> None:
        self.address = address
        self.i2c = SMBus(bus_number)
        self.pga_val = self.pga
        self.mux_val = self.mux

    @property
    def pga(self) -> int:
        self.pga_val = self.pga_reg
        return self.pga_val
    @pga.setter
    def pga(self, value: int) -> None:
        self.pga_reg = value
        self.pga_val = value

    @property
    def mux(self) -> int:
        self.mux_val = self.mux_reg
        return self.mux_val
    @mux.setter
    def mux(self, value: int) -> None:
        self.mux_reg = value
        self.mux_val = value

    @property
    def mode(self) -> int:
        self.mode_val = self.mode_reg
        return self.mode_val
    @mode.setter
    def mode(self, value: int) -> None:
        self.mode_reg = value
        self.mode_val = value

    def voltage(self, mux: int):
        if self.mux_val != mux:
            self.mux = mux
            if self.mode_val == 0:
                time.sleep(0.015)

        if self.mode_val == 1:
            self.operation_status = 1
            time.sleep(0.01)

        res = self.conversion_result
        # print(res)
        if self.pga_val == Gain.TWOTHIRDS:
            return res / 2047.0 * 6.144
        elif self.pga_val == Gain.ONE:
            return res / 2047.0 * 4.096
        elif self.pga_val == Gain.TWO:
            return rest / 2047.0 * 2.048
        elif self.pga_val == Gain.FOUR:
            return res / 2047.0 * 1.024
        elif self.pga_val == Gain.EIGHT:
            return res / 2047.0 * 0.512
        elif self.pga_val == Gain.SIXTEEN:
            return res / 2047.0 * 0.256
        else:
            return 0

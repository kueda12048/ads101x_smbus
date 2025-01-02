import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
from ads101x_smbus import ADS101X_SMBus, Gain, Mux, DataRate
import time

bus_number = 1 # Jetson orin nano
address = 0x48

ads = ADS101X_SMBus(bus_number, address)

#ads.mode = 0 # Continuous mode
ads.mode = 1 # Single-shot mode
ads.pga = Gain.TWOTHIRDS # +/- 6.144V
ads.data_rate = DataRate.SPS_1600

while True:
    print('voltage : %.4f, %.4f, %.4f, %.4f' \
        %(ads.voltage(Mux.AIN0_GND), 
          ads.voltage(Mux.AIN1_GND), 
          ads.voltage(Mux.AIN2_GND), 
          ads.voltage(Mux.AIN3_GND)))
    time.sleep(1.0)

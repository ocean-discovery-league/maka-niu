import time
import smbus
import struct
import os

class KellerLD(object):

	_SLAVE_ADDRESS = 0x40
	_REQUEST_MEASUREMENT = 0xAC
	_DEBUG = False

	def __init__(self, bus=1):
		self._bus = None

		try:
			self._bus = smbus.SMBus(bus)
		except:
			print("Bus %d is not available.") % bus
			print("Available busses are listed as /dev/i2c*")
			if os.uname()[1] == 'raspberrypi':
				print("Enable the i2c interface using raspi-config!")

	def init(self):
		if self._bus is None:
			print("No bus!")
			return False

		# Read out minimum pressure reading
		self._bus.write_byte(self._SLAVE_ADDRESS, 0x13)
		time.sleep(0.001)
		data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)
		
		MSWord = data[1] << 8 | data[2]
		self.debug(("0x13:", MSWord, data))

		time.sleep(0.001)
		self._bus.write_byte(self._SLAVE_ADDRESS, 0x14)
		time.sleep(0.001)
		data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)

		LSWord = data[1] << 8 | data[2]
		self.debug(("0x14:", LSWord, data))

		self.pMin = MSWord << 16 | LSWord
		self.debug(("pMin", self.pMin))

		# Read out maximum pressure reading
		time.sleep(0.001)
		self._bus.write_byte(self._SLAVE_ADDRESS, 0x15)
		time.sleep(0.001)
		data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)
		
		MSWord = data[1] << 8 | data[2]
		self.debug(("0x15:", MSWord, data))

		time.sleep(0.001)
		self._bus.write_byte(self._SLAVE_ADDRESS, 0x16)
		time.sleep(0.001)
		data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 3)

		LSWord = data[1] << 8 | data[2]
		self.debug(("0x16:", LSWord, data))

		self.pMax = MSWord << 16 | LSWord
		self.debug(("pMax", self.pMax))
		
		# 'I' for 32bit unsigned int
		self.pMin = struct.unpack('f', struct.pack('I', self.pMin))[0]
		self.pMax = struct.unpack('f', struct.pack('I', self.pMax))[0]
		self.debug(("pMin:", self.pMin, "pMax:", self.pMax))

		return True

	def read(self):
		if self._bus is None:
			print("No bus!")
			return False
		
		if self.pMin is None or self.pMax is None:
			print("Init required!")
			print("Call init() at least one time before attempting to read()")
			return False

		self._bus.write_byte(self._SLAVE_ADDRESS, self._REQUEST_MEASUREMENT)

		time.sleep(0.01) #10 ms, plenty of time according to spec.

		data = self._bus.read_i2c_block_data(self._SLAVE_ADDRESS, 0, 5)

		statusByte = data[0]
		pressureRaw = data[1] << 8 | data[2]
		temperatureRaw = data[3] << 8 | data[4]

		'''
		# Always busy for some reason
		busy = statusByte & 1 << 5

		if busy:
			print("Conversion is not complete.")
			return
		'''

		if statusByte & 0b11 << 3 :
			print("Invalid mode: %d, expected 0!") % ((statusByte & 0b11 << 3) >> 3)
			return False

		if statusByte & 1 << 2 :
			print("Memory checksum error!")
			return False

		self._pressure = (pressureRaw - 16384) * (self.pMax - self.pMin) / 32768 + self.pMin
		self._temperature = ((temperatureRaw >> 4) - 24) * 0.05 - 50

		self.debug(("data:", data))
		self.debug(("pressureRaw:", pressureRaw, "pressure:", self._pressure))
		self.debug(("temperatureRaw", temperatureRaw, "temperature:", self._temperature))

		return True


	def temperature(self):
		if self._temperature is None:
			print("Call read() first to get a measurement")
			return
		return self._temperature

	def pressure(self):
		if self._pressure is None:
			print("Call read() first to get a measurement")
			return
		return self._pressure

	def debug(self, msg):
		if self._DEBUG:
			print(msg)

if __name__ == '__main__':

	sensor = KellerLD()
	if not sensor.init():
		print("Failed to initialize Keller LD sensor!")
		exit(1)

	while True:
		try:
			sensor.read()
			print("pressure: %7.4f bar\ttemperature: %0.2f C") % (sensor.pressure(), sensor.temperature())
			time.sleep(0.001)
		except Exception as e:
			print(e)

###################################
#This example takes a measurement every second of temperature and pressure
#The pressure is converted to a depth estimate.
#Note that the gauge is rated for 3 to 200 bar, so reading above water are junk
###################################


from kellerLD import KellerLD
import time


sensor = KellerLD()

if not sensor.init():
	print("Failed to initialize Keller LD sensor!")
	exit(1)

print("Testing Keller LD series pressure sensor")
print("Press Ctrl + C to quit")
time.sleep(3)

while True:
	try:
		sensor.read()
		print("pressure: %7.4f bar \t depth: %7.1f meters \t temperature: %0.2f C" % (sensor.pressure(), sensor.pressure()*10 -10, sensor.temperature()))
		time.sleep(1)
	except Exception as e:
		print(e)

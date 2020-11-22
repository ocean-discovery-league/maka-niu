import time
import board
import busio
import adafruit_drv2605

i2c= busio.I2C(board.SCL, board.SDA)
drv = adafruit_drv2605.DRV2605(i2c)

effect_id = 1
while True:
	print("Playing effect #{0}".format(effect_id))
	drv.sequence[0] = adafruit_drv2605.Effect(effect_id)

	drv.play()
	time.sleep(0.5)
	drv.stop()

	effect_id+=1
	if effect_id >123:
		effect_id = 1

#!/usr/bin/sudo /usr/bin/python3
from bluedot.btcomm import BluetoothServer
from signal import pause
from time import sleep
import datetime
import board
import RPi.GPIO as GPIO


def data_received(data):
   #print(data)
   current_dt = datetime.datetime.now()
   date_str = current_dt.strftime("%Y%m%d_%H:%M:%S.%f")[:-3]
   s.send("In:" + date_str)
   green.start(100)
   sleep(0.1)
   green.stop()


GPIO.setmode(GPIO.BCM)
GPIO.setup(13,GPIO.OUT)
green = GPIO.PWM(13,1000)


s = BluetoothServer(data_received)
pause()

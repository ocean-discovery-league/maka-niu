#!/usr/bin/sudo /usr/bin/python3
from bluedot.btcomm import BluetoothClient
from signal import pause
from time import sleep
import datetime
import board
import RPi.GPIO as GPIO


def data_received(data):
   #print(data)
   with open('/home/pi/git/maka-niu/code/log/blue_chat.txt', 'a') as f:
      print(data + "\n", end= "", file = f, flush = True)
   red.start(100)
   sleep(0.1)
   red.stop()


GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
red = GPIO.PWM(12,1000)
green = GPIO.PWM(13,1000)



c = BluetoothClient("mkn0002", data_received)


while 1:
   green.start(100)
   sleep(0.1)
   green.stop()

   current_dt = datetime.datetime.now()
   date_str = current_dt.strftime("%Y%m%d_%H:%M:%S.%f")[:-3]
   c.send(date_str)
   #print("Out:" + date_str)
   sleep(1)
   with open('/home/pi/git/maka-niu/code/log/blue_chat.txt', 'a') as f:
      print("Out:" + date_str, end= "", file = f, flush = True)

#pause()






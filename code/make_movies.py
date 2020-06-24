import picamera
import datetime as dt
import os.path
from os import path

import time
import RPi.GPIO as GPIO

#setup the pi cam settings
camera = picamera.PiCamera()
camera.resolution = (1920,1080)
camera.framerate = 30
#camera.annotate_background = picamera.Color('black')  # this is for overlaid text

#setup LED pwms pins
GPIO.setmode(GPIO.BOARD)
GPIO.setup(33, GPIO.OUT)
GPIO.setup(32, GPIO.OUT)

#flash green once
green = GPIO.PWM(33, 100)
green.start(100)
time.sleep(3)
green.stop(0)

#setup red for recording light blinking
red = GPIO.PWM(32, 0.5)
red.start(0)

#begin recording
print("Hello world, I see you and begining to record.")
if path.exists("allow_filming.txt"): #  dirty way to interact with scripts outside of this python program

#start saving a movie into the 'vid' folder with file name that includes date and time
   start_time = dt.datetime.now()
   clip_name = 'vid/' + start_time.strftime('%Y-%m-%d_%H.%M.%S') + '_MakaNiu.h264'
   camera.start_recording(clip_name, bitrate=10000000) 
   red.ChangeDutyCycle(33.3)

#update the time stamp and overlay into the video file. Stop recording if some other program deletes allow_filming.txt
   while (dt.datetime.now() - start_time).seconds <60 and path.exists("allow_filming.txt"): 
      camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
      camera.wait_recording(1.0)
   camera.stop_recording()

# setup 3 seconds of fast flashing yellow for end
red.stop()
red.ChangeFrequency(100)
for x in range (0,5):
   red.start(10)
   green.start(100)
   time.sleep(.25)
   green.stop()
   red.stop()
   time.sleep(.25)
GPIO.cleanup()
print("Goodbye sweet sweet world. Thank for the footage and memories.")




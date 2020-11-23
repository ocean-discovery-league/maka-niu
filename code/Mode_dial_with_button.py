#!/usr/bin/python
from time import sleep
import RPi.GPIO as GPIO
import array as arr
import sys
from subprocess import call
import board
import busio
import adafruit_drv2605


############################################################### SETUP
#setup i2c for haptic feedback
i2c = busio.I2C(board.SCL, board.SDA)
drv = adafruit_drv2605.DRV2605(i2c)

#setup LED pwms pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
red = GPIO.PWM(12, 1000) #(pin, freq)
#green = GPIO.PWM(13, 100) #(pin, freq)
#//green_duty_cycle = 1.0 # for fading pulse
#//green_pulse_up = 1

#setup Hall sensor pins. All pulled up, so active is when low
GPIO.setup(24, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(10, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(9, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(25, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(11, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(8, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(18, GPIO.IN, pull_up_down = GPIO.PUD_UP)

#establish hall dial variables
hall_button_active = 0
hall_button_last = 0
hall_active = arr.array('i', [0,0,0,0,0,0])
hall_confidence = arr.array('i', [0,0,0,0,0,0])
hall_most_confident_value =0
hall_mode = 0
hall_mode_last = 0
#other variables
time_out_exit = 0
recording = 0 #when recording, you can't change mode willy nilly
end_recording_mode_changed_flag = 0

################################################################# MAIN FOREVER LOOP
print('Welcome. Intitiating LED Dial test program. Enjoy')
sys.stdout.flush()
while True:
   sleep(0.01)

# collect raw hall states, use 1 - GPIO, because they are pull up, active low.
   hall_button_last = hall_button_active #button hall
   hall_button_active = 1-GPIO.input(8)
   hall_active[0] = 1-GPIO.input(11) #mode halls
   hall_active[1] = 1-GPIO.input(25)
   hall_active[2] = 1-GPIO.input(9)
   hall_active[3] = 1-GPIO.input(10)
   hall_active[4] = 1-GPIO.input(24)
   hall_active[5] = 1-GPIO.input(18) #mode hall for power

# determine overall overtime confidence in each hall sensor being active
   for x in range(6):
      if(hall_active[x] and hall_confidence[x] < 100):
         hall_confidence[x] += 1
      elif (hall_active[x] == 0 and hall_confidence[x] > 0):
         hall_confidence[x] -= 1

# pick the mode based on highest hall confidence with score > 5 out of 10
   hall_mode_last = hall_mode
   hall_mode = 0
   for x in range(6):
      if (hall_confidence[x] >= 50):
         hall_mode = 1 + x
   if (recording and hall_mode != 2):
      hall_mode = 2
      end_recording_mode_changed_flag = 1


####################################################################### MODES
#No magnet detected,  no indication
   if (hall_mode == 0 and hall_mode != hall_mode_last):
      print('No hall detected, doing nothing.')
      sys.stdout.flush()
      red.stop()

# Magnet at Wifi Mode,  three red flashes. 
   if (hall_mode == 1):
      if (hall_mode != hall_mode_last):
         print('Wifi Mode actvated. three red flashes')
         sys.stdout.flush()
         drv.sequence[0] = adafruit_drv2605.Effect(58) #58 is solif buzz
         drv.play()
         for x in range(3):
            sleep(0.2)
            red.start(100)
            sleep(0.2)
            red.stop()
         drv.stop()

#Magnet at Video Mode, constant red one. When button pressed, go dark and record video. Press again, end video and start led
   if (hall_mode == 2):
      if (hall_mode != hall_mode_last):
         print('Video Mode activated, press button to begin recording')
         sys.stdout.flush()
         drv.sequence[0] = adafruit_drv2605.Effect(58) #58, 64, 95 are good choice transition buzzes
         drv.play()
         red.start(100)
         recording = 0

      if (hall_button_active != hall_button_last):
         if (hall_button_active and recording == 0):
            #BEGIN RECORDING
            print('Starting video capture now')
            sys.stdout.flush()
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(74) #1
            drv.play()
            red.stop()
            recording = 1

         elif (hall_button_active and recording):
            #END RECORDING
            print('Ending video capture')
            sys.stdout.flush()
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(74) #10 nice double
            drv.play()
            red.start(100)
            recording = 0

      if (end_recording_mode_changed_flag):
         #END RECORDING
         print('Left Camera mode, ending video capture')
         sys.stdout.flush()
         recording = 0
         end_recording_mode_changed_flag = 0




#Magnet at Picture Mode, 5 red flashes.
   if (hall_mode == 3):
      if (hall_mode != hall_mode_last):
         print('Picture Mode activated, 5 flashes. Press button to capture image, hold for burst')
         sys.stdout.flush()
         drv.sequence[0] = adafruit_drv2605.Effect(58)
         drv.play()
         for x in range (5): 
            sleep(0.12)
            red.start(100)
            sleep(0.12)
            red.stop()
      #Flash red both only for press
      if (hall_button_active and hall_button_active != hall_button_last):
         drv.stop()
         drv.sequence[0] = adafruit_drv2605.Effect(74)
         drv.play()
         red.start(100)
         sleep(0.1)
         red.stop()
         sleep(0.15)
         #CAPTURE PHOTO
         print('Photo capture')
         sys.stdout.flush()

      elif (hall_button_active):
         drv.stop()
         drv.sequence[0] = adafruit_drv2605.Effect(80) #17 for solid click
         drv.play()
         #CAPTURE BURST
         print('*')
         sys.stdout.flush()
         sleep(0.25)



#Magnet at Mission 1, one long red flash
   if (hall_mode == 4 and hall_mode != hall_mode_last):
      print('Mission 1 activated')
      sys.stdout.flush()
      drv.sequence[0] = adafruit_drv2605.Effect(58)
      drv.play()
      red.start(100)
      sleep(0.75)
      red.stop()

#Magnet at Mission 2 , flash  red then green twice.
   if (hall_mode == 5 and hall_mode != hall_mode_last):
      print('Mission 2 activated')
      sys.stdout.flush()
      drv.sequence[0] = adafruit_drv2605.Effect(58)
      drv.play()
      red.start(100)
      sleep(0.75)
      red.stop()
      sleep(0.5)
      red.start(100)
      sleep(0.75)
      red.stop()


#Magnet at Power Off Hall,  flash red long, medium, short.
   if (hall_mode == 6 and hall_mode != hall_mode_last):
      print('Powerdown activated')
      sys.stdout.flush()
      drv.sequence[0] = adafruit_drv2605.Effect(47)
      drv.play()
      red.stop()
      for x in range (2): #2 short then long flashes
         red.start(100)
         sleep(0.1)
         red.stop()
         sleep(0.2)
         red.start(100)
         sleep(0.4)
         red.stop()
         sleep(0.2)
      GPIO.cleanup()
      call("sudo shutdown -h now", shell=True)
      sys.exit()

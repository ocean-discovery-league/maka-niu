#!/usr/bin/python
import time
from time import sleep
import os
import RPi.GPIO as GPIO
import array as arr
import sys
from subprocess import call
import board
import busio
import adafruit_drv2605
#import adafruit_lc709203f
import qwiic_titan_gps
from kellerLD import KellerLD

############################################################### SETUP
#setup i2c for haptic feedback and battery fuel gage
i2c = busio.I2C(board.SCL, board.SDA)
drv = adafruit_drv2605.DRV2605(i2c)
drv.sequence[0] = adafruit_drv2605.Effect(58) #58 is solif buzz
drv.play()

#setup i2c for battery fuel gage/ Sadly this module eventually cayses a CRC crash. The library is very new and not well documented/supported.
#battery = adafruit_lc709203f.LC709203F(board.I2C())
#battery.pack_size = adafruit_lc709203f.PackSize.MAH3000 #actually 3500 but not an option
#battery_low_counter = 0

#setup i2c for GPS, would really like to fuse all the i2c into one library
gps = qwiic_titan_gps.QwiicTitanGps()
gps_available = True
if gps.connected is False:
   gps_available = False
   print("Could not connect to GPS.", file = sys.stderr)
   gps.begin()
t = time.time()
have_gps_fix = False

#setup i2c for keller pressure/temperature sensor
outside = KellerLD()
outside.init()


#setup timer for videos
video_started_time = time.time()

#setup LED pwms pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
red = GPIO.PWM(12, 1000) #(pin, freq)

#setup Hall sensor pins. All pulled up, so active is when low
GPIO.setup(8, GPIO.IN, pull_up_down = GPIO.PUD_UP)  #push button
GPIO.setup(11, GPIO.IN, pull_up_down = GPIO.PUD_UP) #wifi mode
GPIO.setup(25, GPIO.IN, pull_up_down = GPIO.PUD_UP) #video mode
GPIO.setup(9, GPIO.IN, pull_up_down = GPIO.PUD_UP)  #photo mode
GPIO.setup(24, GPIO.IN, pull_up_down = GPIO.PUD_UP) #mission 2 mode
GPIO.setup(10, GPIO.IN, pull_up_down = GPIO.PUD_UP) #mission 1 mode
GPIO.setup(18, GPIO.IN, pull_up_down = GPIO.PUD_UP) #power down signal

#hall dial variables
hall_button_active = 0
hall_button_last = 0
hall_active = arr.array('i', [0,0,0,0,0,0])
hall_confidence = arr.array('i', [0,0,0,0,0,0])
hall_most_confident_value =0
hall_mode = 0
hall_mode_last = 0

#other variables
recording = 0 #when recording, you can't change mode willy nilly
end_recording_mode_changed_flag = 0

################################################################# MAIN FOREVER LOOP
print('Maka Niu Python Program Started.')
sys.stdout.flush()
while True:
   sleep(0.01)


# every second, update GPS data, battery info, and pressure/temp info
   if (time.time() - t) > 10:
      t = time.time()
      if gps.connected is True:
         if gps.get_nmea_data() is True:
            for k, v in gps.gnss_messages.items():
               print(k, ":", v)

#        batt_volt = battery.cell_voltage
         batt_volt = 3.5
#        print("Cells at %0.3f Volts" % (batt_volt))
         if batt_volt < 3.1: #BATTERIES Dying!!!
            battery_low_counter +=1
            if battery_low_counter >=5:
               print('Batteries critically low, initiating shutdown.')
               sys.stdout.flush()
               if recording:
                  os.system('echo ca 0 > /var/www/html/FIFO')
                  print('Ending video capture')
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
         else:
            battery_low_counter = 0
      outside.read()
      print("pressure: %7.4f bar \t estimated depth: %7.1f meters \t temperature: %0.2f C\n" % (outside.pressure(), outside.pressure()*10-10, outside.temperature()))
      sys.stdout.flush()

# collect raw hall states, use 1 - GPIO, because they are pull up and active low.
   hall_button_last = hall_button_active
   hall_button_active = 1-GPIO.input(8)  #push button
   hall_active[0] = 1-GPIO.input(11)     #wifi mode
   hall_active[1] = 1-GPIO.input(25)     #video mode
   hall_active[2] = 1-GPIO.input(9)      #photo mode
   hall_active[3] = 1-GPIO.input(10)     #mission 1 mode
   hall_active[4] = 1-GPIO.input(24)     #mission 2 mode
   hall_active[5] = 1-GPIO.input(18)     #powerdown signal

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
         os.system('sudo ifconfig wlan0 up')
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
         #os.system('sudo ifconfig wlan0 down')
         print('Video Mode activated, press button to begin recording')
         sys.stdout.flush()
         drv.sequence[0] = adafruit_drv2605.Effect(58) #58, 64, 95 are good choice transition buzzes
         drv.play()
         red.start(100)
         recording = 0

      if (hall_button_active != hall_button_last):
         if (hall_button_active and recording == 0):
            #BEGIN RECORDING
            os.system('echo ca 1 > /var/www/html/FIFO')
            print('Starting video capture now')
            sys.stdout.flush()
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(74) #1
            drv.play()
            red.stop()
            recording = 1
            video_started_time = time.time()

         elif (hall_button_active and recording):
            #END RECORDING
            os.system('echo ca 0 > /var/www/html/FIFO')
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

      if (recording and (time.time()-video_started_time) > 899):
         os.system('echo ca 0 > /var/www/html/FIFO')
         print('Video capture time limit reached: Start new capture')
         sys.stdout.flush()
         sleep(0.5)
         os.system('echo ca 1 > /var/www/html/FIFO')
         sys.stdout.flush()
         video_started_time = time.time()


#Magnet at Picture Mode, 5 red flashes.
   if (hall_mode == 3):
      if (hall_mode != hall_mode_last):
         #os.system('sudo ifconfig wlan0 down')
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
         os.system('echo im 1 > /var/www/html/FIFO')
         print('Photo capture')
         sys.stdout.flush()

      elif (hall_button_active):
         drv.stop()
         drv.sequence[0] = adafruit_drv2605.Effect(17) #17 for solid click , 80 for short vib
         drv.play()
         #CAPTURE BURST
         os.system('echo im 1 > /var/www/html/FIFO')
         print('*')
         sys.stdout.flush()
         sleep(0.25)



#Magnet at Mission 1, one long red flash
   if (hall_mode == 4 and hall_mode != hall_mode_last):
      os.system('sudo ifconfig wlan0 down')
      print('Mission 1 activated')
      sys.stdout.flush()
      drv.sequence[0] = adafruit_drv2605.Effect(58)
      drv.play()
      red.start(100)
      sleep(0.75)
      red.stop()

#Magnet at Mission 2 , flash  red then green twice.
   if (hall_mode == 5 and hall_mode != hall_mode_last):
      os.system('sudo ifconfig wlan0 down')
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
from time import sleep 
import RPi.GPIO as GPIO 
import array as arr
import sys

#setup LED pwms pins and Hall sensor pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
red = GPIO.PWM(12, 0.5)
green = GPIO.PWM(13, 100)
GPIO.setup(24, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(10, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(9, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(25, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(11, GPIO.IN, pull_up_down = GPIO.PUD_UP)

#establish hall dial variables
hall_active = arr.array('i', [0,0,0,0,0])
hall_confidence = arr.array('i', [0,0,0,0,0])
hall_mode = 0
hall_mode_last = 0
time_out_exit = 0

# start main forever loop
print('Welcome')
sleep(1.5)
print('Intitiating LED Dial test program. Enjoy')
while True:
   sleep(0.1)

# collect raw hall states
   hall_active[0] = GPIO.input(24)
   hall_active[1] = GPIO.input(10)
   hall_active[2] = GPIO.input(9)
   hall_active[3] = GPIO.input(25)
   hall_active[4] = GPIO.input(11)

# determine overall overtime confidence in each hall sensor being active
   for x in range(5):
      if(hall_active[x] ==0 and hall_confidence[x] < 10):
         hall_confidence[x] += 1
      elif (hall_active[x] == 1 and hall_confidence[x] > 0):
         hall_confidence[x] -= 1

# pick the mode based on high hall confidence (simple but dumb method, what if two are high?)
   hall_mode_last = hall_mode
   hall_mode = 0
   for x in range(5):
      if (hall_confidence[x] >= 5):
         hall_mode = 1 + x

# operate based on chosen mode
   if (hall_mode == 0 and hall_mode != hall_mode_last):
      print('No mode selected')
      green.stop()
      red.stop()
      #no LED

   if (hall_mode == 1 and hall_mode != hall_mode_last):
      print('Mode 1 activated')
      red.stop()
      green.ChangeFrequency(100)
      green.start(100)
      #green On

   if (hall_mode == 2 and hall_mode != hall_mode_last):
      print('Mode 2 activated')
      red.stop()
      green.ChangeFrequency(10)
      green.start(50)
      #fast blinky green

   if (hall_mode == 3 and hall_mode != hall_mode_last):
      print('Mode 3 activated')
      green.ChangeFrequency(100)
      red.ChangeFrequency(100)
      green.start(50)
      red.start(5)
      #yellow

   if (hall_mode == 4 and hall_mode != hall_mode_last):
      print('Mode 4 activated')
      green.stop()
      red.ChangeFrequency(10)
      red.start(50)
      #red On

   if (hall_mode == 5 and hall_mode != hall_mode_last):
      print('Mode 5 activated')
      green.stop()
      red.ChangeFrequency(100)
      red.start(10)
      #fast blinky red

   if (hall_mode == 0):
      time_out_exit +=1
      if (time_out_exit > 500):
         print('No signal. Exiting program.')
         GPIO.cleanup()
         sys.exit()
   else:
     time_out_exit = 0
     #exit program if no hall for long time





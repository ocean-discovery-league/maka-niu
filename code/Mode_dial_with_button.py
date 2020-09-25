#!/usr/bin/python
from time import sleep
import RPi.GPIO as GPIO
import array as arr
import sys
from subprocess import call



############################################################### SETUP
#setup LED pwms pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
red = GPIO.PWM(12, 100) #(pin, freq)
green = GPIO.PWM(13, 100) #(pin, freq)
green_duty_cycle = 1.0 # for fading pulse
green_pulse_up = 1
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
   if (recording and hall_mode != hall_mode_last):
      hall_mode = hall_mode_last
      end_recording_mode_changed_flag = 1


####################################################################### MODES
#No magnet detected, unit is off, no LEDs
   if (hall_mode == 0 and hall_mode != hall_mode_last):
      print('No hall detected, doing nothing')
      sys.stdout.flush()
      green.stop()
      red.stop()

# Magnet at Wifi Mode,  solid green
   if (hall_mode == 1):
      if (hall_mode != hall_mode_last):
         print('Wifi Mode actvated. Solid green led')
         red.stop()
         green.start(100)

#Magnet at Video Mode, soft pulsing green. When button pressed, pulse red 3x, then go dark and record video. Press again, blink red 2X and end video
   if (hall_mode == 2):
      if (hall_mode != hall_mode_last):
         print('Video Mode activated, press button to begin recording')
         green_duty_cycle = 5
         red.stop()

      if (recording == 0):
         green.start(5+green_duty_cycle)
         if (green_duty_cycle <1):
            green_pulse_up = 1
         elif (green_duty_cycle >90):
            green_pulse_up = 0
         if (green_pulse_up):
            green_duty_cycle = green_duty_cycle * 1.05
         else:
            green_duty_cycle = green_duty_cycle * 0.95

      if (hall_button_active != hall_button_last):
         if (hall_button_active and recording == 0):
            green.stop()
            led_duty_cycle = 1
            pulse_up =1
            pulse_count =0

            while (pulse_count < 3):
               sleep(0.01)
               red.start(led_duty_cycle)
     	       if (led_duty_cycle <3 and pulse_up == 0):
                  pulse_up = 1
                  pulse_count = pulse_count +1
               elif (led_duty_cycle >80 and pulse_up):
        	  pulse_up = 0
               if (pulse_up):
                  led_duty_cycle = led_duty_cycle * 1.1
               else:
                  led_duty_cycle = led_duty_cycle * 0.9

            red.stop()
            #BEGIN RECORDING
            print('Starting video now')
            recording = 1

         elif (hall_button_active and recording):
            red.ChangeFrequency(3)
            red.start(50)
	    sleep(1)
            red.stop()
            red.ChangeFrequency(100)
            #END RECORDING
            print('Ending video')
            recording = 0
            sleep(0.5)
            green.ChangeFrequency(100)
            green.start(100)

      if (end_recording_mode_changed_flag):
         red.ChangeFrequency(3)
         red.start(50)
         sleep(1)
         red.stop()
         red.ChangeFrequency(100)
         green.stop()
	 #END RECORDING
         print('Ending video')
         recording = 0
         sleep(0.5)




#Magnet at Picture Mode, pulsing yellow, flash red when button pressed (dont stay on) and capture photo. If button continued to press, take photos as long as button is pressed.
   if (hall_mode == 3):
      if (hall_mode != hall_mode_last):
         print('Picture Mode activated, pulsing yellow. Press button to capture image, hold for burst')

      if (hall_button_active):
         green_duty_cycle = 3
         if (hall_button_active != hall_button_last):
            #flash red
            green.stop()
            red.start(100)
            sleep(0.25)
            red.stop()
            #CAPTURE PHOTO
            sleep(0.5)
         else :
            #CAPTURE BURST PHOTO
            sleep(0.25)
      else :
         green.start(5 + green_duty_cycle)
         red.start(5 + green_duty_cycle)
         if (green_duty_cycle <1):
            green_pulse_up = 1
         elif (green_duty_cycle >50):
            green_pulse_up = 0
         if (green_pulse_up):
            green_duty_cycle = green_duty_cycle * 1.05
         else:
            green_duty_cycle = green_duty_cycle * 0.95

#Magnet at Mission 1, flash red then flash green once
   if (hall_mode == 4 and hall_mode != hall_mode_last):
      print('Mission 1 activated')
      green.stop()
      red.stop()
      sleep(0.5)
      red.start(100)
      sleep(0.25)
      red.stop()
      for x in range (1):
         sleep(0.5)
         green.start(100)
         sleep(0.75)
         green.stop()
      #sleep(0.5)
      #red.start(100)
      #sleep(0.25)
      #red.stop()



#Magnet at Mission 2 , flash  red then green twice.
   if (hall_mode == 5 and hall_mode != hall_mode_last):
      print('Mission 2 activated')
      green.stop()
      red.stop()
      sleep(0.5)
      red.start(100)
      sleep(0.25)
      red.stop()
      for x in range (2):
         sleep(0.5)
         green.start(100)
         sleep(0.75)
         green.stop()
      #sleep(0.5)
      #red.start(100)
      #sleep(0.25)
      #red.stop()

#Magnet at Power Off Hall,  flash red long, medium, short.
   if (hall_mode == 6 and hall_mode != hall_mode_last):
      print('Powerdown activated')
      green.stop()
      red.stop()
      for x in range (3): #3 fast flashes and start shutdown
         sleep(0.16)
         red.start(100)
         sleep(0.16)
         red.stop()
      GPIO.cleanup()
      call("sudo shutdown -h now", shell=True)
      sys.exit()
   #if (hall_mode == 0):
    #  time_out_exit +=1
     # if (time_out_exit > 50):
      #   print('No signal. Exiting program.')
       #  GPIO.cleanup()
        # sys.exit()
   #else:
    # time_out_exit = 0
     #exit program if no hall for long time





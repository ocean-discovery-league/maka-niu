#!/usr/bin/sudo /usr/bin/python3
import datetime
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
import spidev
import qwiic_titan_gps
from kellerLD import KellerLD


############################################################### FUCNTIONS
def getBatteryVoltage(vref = 3.3):
   msg = 0b11
   msg = ((msg << 1) + 0) << 5
   msg = [msg, 0b00000000]
   reply = spi.xfer2(msg)
   adc = 0
   for n in reply:
      adc = (adc << 8) + n
   adc = adc >> 1
   voltage = (vref * adc)/1024
   pack_voltage = voltage * 4 + 0.3 # adc * voltage + plus diode forward drop
   return pack_voltage



############################################################### SETUP
serial_number= "MKN0001"

#To avoid messing with clocks, we are creating a date time offset variable that will be used for timestamping 
datetime_offset = datetime.timedelta(0)
print(datetime.datetime.now())



#setup a 60 seconds timer to disable HDMI output, that way for debug its still possible to connect a screen and end this program.
hdmi_end_timer = time.time()
hdmi_enabled = True

#setup LED pwms pins for feedback
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
red = GPIO.PWM(12, 1000) #(pin, freq)
green = GPIO.PWM(13, 1000) #(pin, freq)

#setup GPIO pin  that enables 3.3V regulator powering GPS, Keller, IMU.
GPIO.setup(18, GPIO.OUT)
GPIO.output(18, GPIO.HIGH) #can potentially set low to preserve a little power
sleep(0.5)

#setup SPI for battery ADC via MCP3002 and a 100K/33K voltage divider on the battery pack voltage
battery_low_counter = 0
battery_volt = 12
adc_connected = True
try:
   spi = spidev.SpiDev(1,2)
   spi.max_speed_hz = 10000
   battery_volt = getBatteryVoltage()
   print("Starting battery voltage:" , round(battery_volt,3), "V")
except:
   print("ADC not connected, SPI fail")
   adc_connected = False

if battery_volt < 5 or battery_volt > 15:
   print("ADC not connected, values out of range.")
   adc_connected = False
   battery_volt = 12

if battery_volt < 9.0:
   print('Batteries critically low, initiating shutdown in 60 seconds.')
   sys.stdout.flush()
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
   sleep(60)
   GPIO.cleanup()
   call("sudo shutdown -h now", shell=True)
   sys.exit()


#setup i2c for haptic feedback and battery fuel gage
i2c = busio.I2C(board.SCL, board.SDA)
haptic_connected = True
try:
   drv = adafruit_drv2605.DRV2605(i2c)
   drv.sequence[0] = adafruit_drv2605.Effect(58) #58 is solif buzz
   drv.play()
except:
   print("Haptic feedback not connected.")
   haptic_connected = False


#setup i2c for GPS, would really like to fuse all the i2c into one library
gps = qwiic_titan_gps.QwiicTitanGps()
gps_connected = True
if gps.connected is False:
   gps_connected = False
   print("GPS device not connected.", file = sys.stderr)
gps.begin()


#setup i2c for keller pressure/temperature sensor
outside = KellerLD()
keller_connected = True
try:
   outside.init()
except:
   keller_connected = False
   print("Keller LD sensor not connected.")

#setup Hall sensor pins. All pulled up, so active is when low
GPIO.setup(8, GPIO.IN, pull_up_down = GPIO.PUD_UP)  #push button
GPIO.setup(11, GPIO.IN, pull_up_down = GPIO.PUD_UP) #wifi mode
GPIO.setup(25, GPIO.IN, pull_up_down = GPIO.PUD_UP) #video mode
GPIO.setup(9, GPIO.IN, pull_up_down = GPIO.PUD_UP)  #photo mode
GPIO.setup(24, GPIO.IN, pull_up_down = GPIO.PUD_UP) #mission 2 mode
GPIO.setup(10, GPIO.IN, pull_up_down = GPIO.PUD_UP) #mission 1 mode
GPIO.setup(14, GPIO.IN, pull_up_down = GPIO.PUD_UP) #power down signal

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
end_recording_mode_changed_flag = 0 #flag to end video if mode changes
photo_burst_time = time.time() #to manag time delay between images in burtst
interface_rotation = 0 # alternate i2c jobs and spi job to minimize delay
video_started_time = time.time() # for chopping video to fixed max lentgh
t = time.time() # for timing interface comms


################################################################# MAIN FOREVER LOOP
print('Maka Niu Program iniated. Entering main forever loop.')
sys.stdout.flush()


if adc_connected and gps_connected and keller_connected:
   print('ADC, GPS, and Keller hardware all talking.')
#red.start(100)
   green.start(100)
sleep(3) #demanded by keller but also used for all OK LED
#red.stop()
green.stop()


while True:
   sleep(0.01)
   green.stop()

# every second, update GPS data, battery info, and pressure/temp info, rotate to minimize time gaps
   if (time.time() - t) > 0.33:
      t = time.time()
      interface_rotation +=1
      if gps_connected and interface_rotation == 1 and hall_button_active==0: #gps takes a logn time and interferes with photo burst
         try:
            if gps.connected is True:
               if gps.get_nmea_data() is True:
                  if (gps.gnss_messages["Status"]) == 'A':
                     green.start(100)
                     print("Have Fix")

                     #check that the date time stamps are in valid format, and if yes, use for local time update
                     if isinstance(gps.gnss_messages["Date"], datetime.date) and isinstance(gps.gnss_messages["Time"], datetime.time):
                        datetime_gps = datetime.datetime.combine(gps.gnss_messages["Date"],gps.gnss_messages["Time"])
                        datetime_offset = datetime_gps - datetime.datetime.now()

                        #PRINT TO SENSOR FILE TEST
                        if recording and sensor_file.closed == False:
                           print("GNSS:{}_{}_{}".format(
                              (datetime.datetime.now() + datetime_offset).isoformat(sep='_', timespec = 'seconds'),
                              gps.gnss_messages["Latitude"],
                              gps.gnss_messages["Longitude"]), file=sensor_file)
                              #time_stamp = datetime.datetime.now()+datetime_offset

                  print("UTC Datetime: {} {}\nLatitude: {}\nLongitude: {}".format(
                     gps.gnss_messages["Date"],
                     gps.gnss_messages["Time"],
                     gps.gnss_messages["Latitude"],
                     gps.gnss_messages["Longitude"]))
         except:
            print("GPS error of some kind.")

      elif adc_connected and interface_rotation == 2:
         reading = getBatteryVoltage()
         if reading < 15 and reading > 5:
            battery_volt = battery_volt*0.9 + reading*0.1
         print("Battery Pack at at %0.3f Volts" % (battery_volt))
         if recording and sensor_file.closed == False:
            print("BATT:{}_{:.2f}".format(
               (datetime.datetime.now()+ datetime_offset).isoformat(sep='_',timespec='seconds'), 
               battery_volt), file=sensor_file)
         if battery_volt < 9.0: #BATTERIES Dying!!!
            battery_low_counter +=1
            if battery_low_counter >=5:
               print('Batteries critically low, ending processes now, initiating shutdown in 60 seconds.')
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
               sleep(60)
               GPIO.cleanup()
               call("sudo shutdown -h now", shell=True)
               sys.exit()
         else:
            battery_low_counter = 0

      elif keller_connected and interface_rotation ==3:
         try:
            outside.read()
            approx_depth = outside.pressure()*10+10
            print("pressure: %7.4f bar \t estimated depth: %7.1f meters \t temperature: %0.2f C\n" % (outside.pressure(), approx_depth, outside.temperature()))
            sys.stdout.flush()
            if recording and sensor_file.closed == False:
               print("KELL:{}_P{:.2f}_D{:.1f}_T{:.2f}".format(
               (datetime.datetime.now()+ datetime_offset).isoformat(sep='_',timespec='seconds'),
               outside.pressure(), approx_depth, outside.temperature()), file=sensor_file)
         except Exception as e:
            print(e)

      interface_rotation %= 3

   if hdmi_enabled == True and (time.time() - hdmi_end_timer > 60):
      os.system('/usr/bin/tvservice -o')
      os.system('echo none | sudo tee /sys/class/leds/led0/trigger')
      os.system('echo 0 | sudo tee /sys/class/leds/led0/brightness')
      print('*******60 seconds elapsed since start. HDMI and ACT LED disabled.*******')
      hdmi_enabled = False


# collect raw hall states, use 1 - GPIO, because they are pull up and active low.
   hall_button_last = hall_button_active
   hall_button_active = 1-GPIO.input(8)  #push button
   hall_active[0] = 1-GPIO.input(11)     #wifi mode
   hall_active[1] = 1-GPIO.input(25)     #video mode
   hall_active[2] = 1-GPIO.input(9)      #photo mode
   hall_active[3] = 1-GPIO.input(10)     #mission 1 mode
   hall_active[4] = 1-GPIO.input(24)     #mission 2 mode
   hall_active[5] = 1-GPIO.input(14)     #powerdown signal

# determine overall overtime confidence in each hall sensor being active
   for x in range(6):
      if(hall_active[x] and hall_confidence[x] < 25):
         hall_confidence[x] += 1
      elif (hall_active[x] == 0 and hall_confidence[x] > 0):
         hall_confidence[x] -= 1

# pick the mode based on highest hall confidence with score > 5 out of 10
   hall_mode_last = hall_mode
   hall_mode = 0
   for x in range(6):
      if (hall_confidence[x] >= 15):
         hall_mode = 1 + x
   if (recording and hall_mode != 6 and hall_mode!=2):
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
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58) #58 is solif buzz
            drv.play()
         for x in range(3):
            sleep(0.2)
            red.start(100)
            sleep(0.2)
            red.stop()
         if haptic_connected:
            drv.stop()

#Magnet at Video Mode, constant red one. When button pressed, go dark and record video. Press again, end video and start led
   if (hall_mode == 2):
      if (hall_mode != hall_mode_last):
         #os.system('sudo ifconfig wlan0 down')
         print('Video Mode activated, press button to begin recording')
         sys.stdout.flush()
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58) #58, 64, 95 are good choice transition buzzes
            drv.play()
         red.start(100)
         recording = 0

      if (hall_button_active != hall_button_last):
         if (hall_button_active and recording == 0):
            #BEGIN RECORDING. 1st determine video file name, and create same named sensor data file
            time_stamp = datetime.datetime.now()+datetime_offset
            filename = serial_number + "_" + time_stamp.isoformat("_","milliseconds")
            with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
               print(filename , end="", file=f)
            sensor_file = open("/var/www/html/media/{}{}".format(filename,".txt"), 'w')
            #sensor_file = open("{}{}".format(filename,".txt"), 'w')
            os.system('echo ca 1 > /var/www/html/FIFO')
            print('Starting video capture')
            sys.stdout.flush()

            if haptic_connected:
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
            if haptic_connected:
               drv.stop()
               drv.sequence[0] = adafruit_drv2605.Effect(74) #10 nice double
               drv.play()
            red.start(100)
            #cleanup, clear recording flag and close the sensor data file
            recording = 0
            sensor_file.close()

      if (end_recording_mode_changed_flag):
         #END RECORDING
         print('Left Camera mode, ending video capture')
         sys.stdout.flush()
         #cleanup, clear recording flag and close the sensor data file
         recording = 0
         sensor_file.close()
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
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()
         for x in range (5): 
            sleep(0.12)
            red.start(100)
            sleep(0.12)
            red.stop()
      #Flash red both only for press
      if (hall_button_active and hall_button_active != hall_button_last):
         if haptic_connected:
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(74)
            drv.play()
         red.start(100)
         sleep(0.1)
         red.stop()
         sleep(0.15)
         #CAPTURE PHOTO
         time_stamp = datetime.datetime.now()+datetime_offset
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(serial_number,time_stamp.isoformat("_","milliseconds"), sep ='_' , end="", file=f)
         os.system('echo im 1 > /var/www/html/FIFO')
         print('\nPhoto capture')
         sys.stdout.flush()

      elif (hall_button_active and (time.time() - photo_burst_time > 0.24)):
         photo_burst_time = time.time()
         if haptic_connected:
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(17) #17 for solid click , 80 for short vib
            drv.play()
         #CAPTURE BURST
         time_stamp = datetime.datetime.now()+datetime_offset
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(serial_number,time_stamp.isoformat("_","milliseconds"), sep ='_' , end="", file=f)
         os.system('echo im 1 > /var/www/html/FIFO')
         print('*')
         sys.stdout.flush()



#Magnet at Mission 1, one long red flash
   if (hall_mode == 4 and hall_mode != hall_mode_last):
      os.system('sudo ifconfig wlan0 down')
      print('Mission 1 activated')
      sys.stdout.flush()
      if haptic_connected:
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
      if haptic_connected:
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
      if haptic_connected:
         drv.sequence[0] = adafruit_drv2605.Effect(47)
         drv.play()
      red.stop()
      for x in range (2): #2 short then long flashes
         red.start(100)
         sleep(0.05)
         red.stop()
         sleep(0.1)
         red.start(100)
         sleep(0.2)
         red.stop()
         sleep(0.04)
      GPIO.cleanup()
      call("sudo shutdown -h now", shell=True)
      sys.exit()


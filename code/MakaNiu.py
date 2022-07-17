#!/usr/bin/sudo /usr/bin/python3
import logging
import logging.handlers
import glob
import datetime
import time
from time import sleep
import os
import RPi.GPIO as GPIO
import array as arr
import sys
import subprocess
from subprocess import call
import board
import busio
import adafruit_drv2605
import spidev
import qwiic_titan_gps
import qwiic_icm20948
from kellerLD import KellerLD
import socket
import re, uuid

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


#############################################################SETUP ERROR AND DEBUG LOGGING
#name of the next log file
LOG_FILENAME = '/home/pi/git/maka-niu/code/log/MakaNiu_debug.log'

#create logging objects
logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)

#setup up to 0 backup log files, meaning we keep logs of last 10 runtimes
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, backupCount = 9)
logger.addHandler(handler)

#determine if any log file exist and if yes all existing logs need to rolloverm then print the list
needRoll = os.path.isfile(LOG_FILENAME)
if needRoll:
   logger.handlers[0].doRollover()

#and now make all debug message also print to console
logger.addHandler(logging.StreamHandler(sys.stdout))


############################################################### SETUP

#control variables: change these as desired
mac_address = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
serial_number = socket.gethostname()
mission1_name = "M1" #can be user specified
mission2_name = "M2" #can be user specified
hdmi_act_led_timeout_seconds = 90
battery_low_shutdown_timeout_seconds = 60
video_timelimit_seconds = 900 # 15 minutes

#To avoid messing with pi's clock, we are creating a UTC datetime offset variable that will be used for timestamping filenames and sensor data
datetime_offset = datetime.timedelta(0)

#print code version, date time and unit serial number
version = subprocess.check_output(["git", "describe", "--always"], cwd=os.path.dirname(os.path.abspath(__file__))).strip().decode()
logger.debug("Serial number: {}\tPi datetime: {}\tMAC: {}\tCode versin: {}".format(serial_number, datetime.datetime.now(), mac_address, version))
with open('/home/pi/git/maka-niu/code/log/version.txt', 'w') as f:
   print("{}".format(version), end="", file=f, flush= True)


#setup a timer to disable HDMI output, that way for debug it is still possible to connect a screen and end this program before hdmi cuts.
hdmi_end_timer = time.time()
hdmi_enabled = True

#setup LED pwms pins for feedback
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
red = GPIO.PWM(12, 1000) #(pin, freq)
green = GPIO.PWM(13, 1000) #(pin, freq)

#setup the GPIO pin that enables 3.3V regulator in the BMS board that powers GPS, Keller, IMU.
GPIO.setup(18, GPIO.OUT)
#GPIO.output(18, GPIO.LOW) #NOTE: for debug only
#sleep(0.5)
GPIO.output(18, GPIO.HIGH) #NOTE: is a mission has long standby time and the peripherals are not needed, one may set this pin low to preserve power
sleep(0.5)

#setup SPI for battery ADC via MCP3002 and a 100K/33K voltage divider on the battery pack voltage
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
battery_low_counter = 0
battery_volt = 12
adc_connected = True
try:
   spi = spidev.SpiDev(1,2)
   spi.max_speed_hz = 10000
   battery_volt = getBatteryVoltage()
   logger.debug("Starting battery voltage: {}V".format(round(battery_volt,3)))

except:
   logger.error("ADC not connected, SPI Exception")
   adc_connected = False

if battery_volt < 5 or battery_volt > 15:
   logger.debug("ADC not connected, values out of range.")
   adc_connected = False
   battery_volt = 12

#If the batteries are already depleted at start of runtime, initiate shutdown with a timeout to allow for user to intercept
if battery_volt < 9.0:
   logger.debug('Batteries critically low, initiating shutdown in 60 seconds.')
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
   sleep(battery_low_shutdown_timeout_seconds)
   GPIO.cleanup()
   call("sudo shutdown -h now", shell=True)
   sys.exit()

#setup i2c for haptic feedback
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
i2c = busio.I2C(board.SCL, board.SDA)
haptic_connected = True
try:
   drv = adafruit_drv2605.DRV2605(i2c)
   drv.sequence[0] = adafruit_drv2605.Effect(58) #58 is solid buzz
   drv.play()
   logger.debug("Haptic feedback device connected")
except:
   logger.error("Haptic feedback not connected. Exception")
   haptic_connected = False

#setup i2c for GPS
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
gps = qwiic_titan_gps.QwiicTitanGps()
gps_connected = True
if gps.connected is False:
   gps_connected = False
   logger.error("GPS device not connected.")
else:
   logger.debug("GPS device connected")
gps.begin()


#setup i2c for keller pressure/temperature sensor
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
outside = KellerLD()
keller_connected = True
try:
   outside.init()
   logger.debug("Keller sensor connected")

except:
   keller_connected = False
   logger.error("Keller LD sensor not connected. Exception")

#setup i2c for IMU sensor
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
imu_connected = True
try:
   imu = qwiic_icm20948.QwiicIcm20948()
   if imu.connected == False:
      imu_connected = False
      logger.error("IMU sensor not connected")
   else:
      imu.begin()
      imu.setFullScaleRangeAccel(0x02) #+-8G forces
      imu.setFullScaleRangeGyro(0x00) #250 degrees per second
      logger.debug("IMU sensor connected")
except:
   imu_connected = False
   logger.error("IMU sensor not connected. Exception")

#setup hall sensor GPIO pins. All pulled up, so active is when low
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
hall_active = arr.array('i', [0,0,0,0,0,0]) #binary active or not
hall_confidence = arr.array('i', [0,0,0,0,0,0]) #gradient confidence
hall_most_confident_value =0
hall_mode = 0
hall_mode_last = 0

#other variables
recording = 0 #when recording, this flag is set so that modes changes are limited /prevented
end_processes_mode_changed_flag = 0 #flag to properly end videos and sensor data files when mode changes
photo_burst_time = time.time() #to manage time delay between images in burst
interface_rotation = 0 #alternate various i2c jobs and battery spi job to minimize delay
video_started_time = time.time() # for limiting video to fixed max lentgh segments
interfaces_time = time.time() # for timing interface comms
in_mission =0 # either not in a mission, or in mission 1 or 2.
fix_time_stamp= time.time()
fix_achieved_this_runtime = False
fix_is_live = False
fix_latitude = 0.0
fix_longitude = 0.0
fix_last_UTC_update = datetime.datetime.now()
gnss_string = ""
batt_string = ""
kell_string = ""
imu_string = ""
clock_updated_this_runtime = False
wifi_enabled = True


#setup keller depth offset calibration
approx_depth = 0
uncalibrated_depth = 0
keller_depth_offset = 0
if os.path.exists('/home/pi/git/maka-niu/code/log/keller_offset.txt'):
   with open('/home/pi/git/maka-niu/code/log/keller_offset.txt', 'r+') as k:

      try:
         depth_string = k.readline()
         keller_depth_offset = float(depth_string)
         logger.debug('Initial keller depth offset of {} loaded.'.format(keller_depth_offset))

      except:
         keller_depth_offset = 0
         k.seek(0)
         print("{}".format(keller_depth_offset) , end="", file=k, flush= True)
         k.truncate()
         logger.error("Error reading keller offset value. Wrote 0 to offset file")


#If all the hardware interfaces appear to be functioning, turn the green len on for 3 seconds
if adc_connected and gps_connected and keller_connected:
   logger.debug('ADC, GPS, and Keller hardware all talking.')
   green.start(100)
   sleep(3)
red.stop()
green.stop()

#Print to stream that setup is over
logger.debug('Maka Niu Program setup complete Entering main forever loop.')


################################################################# MAIN FOREVER LOOP
while True:
   #short delay to run at 100hz(actually likely much less due to all the other operations.)
   sleep(0.01)
   #disable green led that gets turned on every second if gps has a fix, this creates a 1 hz green indicator of fix.
   green.stop()

   #every second, update GPS data, battery info, and pressure/temp info. Rotate through tasks to minimize time gaps
   if (time.time() - interfaces_time) > 0.24:
      interfaces_time = time.time()
      interface_rotation +=1

      #get GPS data. This is fairly slow, so skip this step if burst photo is active, as it messes with timing
      if gps_connected and interface_rotation == 1: # and hall_button_active==0:

         #Use try/except to prevent crash from i2c
         try:
            if gps.connected is True:
               if gps.get_nmea_data() is True:
                  if (gps.gnss_messages["Status"]) == 'A': # Status 'A' means GPS has a fix
                     #setup a green flash
                     fix_is_live = True
                     green.start(100)

                     #check that the date time stamps are in valid format, sometimes they are not. If ok, update the local UTC timestamp offset
                     if isinstance(gps.gnss_messages["Date"], datetime.date) and isinstance(gps.gnss_messages["Time"], datetime.time):

                        #if both date and time data is good, combine them into one datetime object
                        datetime_gps = datetime.datetime.combine(gps.gnss_messages["Date"],gps.gnss_messages["Time"]).replace(microsecond = 0)
                        proposed_datetime_offset = datetime_gps - datetime.datetime.now()

                        #sometimes the gps gives back the same time multiple times, and so can give slighly outdated time.
                        #That is small but reversing the clock results in sensor data with timestamp out of order.
                        #So we will only update time if the GPS moves times forward, that way sensor data timestamps are consistent
                        if proposed_datetime_offset > datetime_offset :
                           datetime_offset = proposed_datetime_offset
                           clock_updated_this_runtime = True
                           logger.debug("Datetime offset set to {} with status A".format(datetime_offset))
                           logger.debug("Current UTC with offset is {}".format((datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-','')))


                        #check that the latitude and longitude appear to be in valid format, sometimes they are not.
                        if isinstance(gps.gnss_messages["Latitude"],float) and isinstance(gps.gnss_messages["Longitude"],float):

                           #Now we are confident in both time and location
                           #record the pi time at time of good fix as well as the new longitude and latitude
                           fix_achieved_this_runtime = True
                           fix_time_stamp = time.time() #this number is for calculating fix age later for photos.
                           fix_latitude = gps.gnss_messages["Latitude"]
                           fix_longitude = gps.gnss_messages["Longitude"]

                           #If data looks valid, print GPS data to console and to any open sensor file.
                           gnss_string = "{}\t{:.7f}\t{:.7f}".format(
                              (datetime.datetime.now() + datetime_offset).isoformat(sep='\t', timespec = 'milliseconds').replace(':', '').replace('-', ''),
                              gps.gnss_messages["Latitude"],
                              gps.gnss_messages["Longitude"])
                           print("GNSS:{}".format(gnss_string))
                           if (recording or in_mission) and sensor_file.closed == False:
                              print("GNSS:{}\t{}".format(time.monotonic_ns(),gnss_string), file=sensor_file, flush=True)

                           #write status to status file
                           keller_depth_offset = keller_depth_offset*0.99 + uncalibrated_depth*0.01
                           with open('/home/pi/git/maka-niu/code/log/keller_offset.txt', 'w') as f:
                              print("{}".format(keller_depth_offset) , end="", file=f, flush= True)

                  #Just once on start up, if we dont have an immediate fix, let's consider still updating the pi clock just once when we get a seemingly valid potential date from the gps
                  elif clock_updated_this_runtime == False and isinstance(gps.gnss_messages["Date"], datetime.date) and isinstance(gps.gnss_messages["Time"], datetime.time):

                     #only doing this once
                     clock_updated_this_runtime = True

                     #if both date and time data is good, combine them into one datetime object
                     datetime_gps = datetime.datetime.combine(gps.gnss_messages["Date"],gps.gnss_messages["Time"]).replace(microsecond = 0)

                     #if the retreaved date time is past january 2021, and is newer than the Pi's clock
                     if datetime_gps > datetime.datetime(2021,1,1) and datetime_gps > datetime.datetime.now():
                        datetime_offset = datetime_gps - datetime.datetime.now()
                        logger.debug("Datetime offset set to {} at startup".format(datetime_offset))
                        logger.debug("Current UTC with offset is {}".format((datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-','')))

                  else:
                     fix_is_live = False

         except Exception as e:
            logger.error("@GNSS\n{}".format(e))

      #get battery voltage ADC via SPI interface, dont update during photo burst
      if adc_connected and interface_rotation == 2: # and hall_button_active ==0:

         #Get the adc and then since it is a bit noisy, apply a running average
         reading = getBatteryVoltage()
         if reading < 15 and reading > 5:
            battery_volt = battery_volt*0.9 + reading*0.1

         #print voltage to stream, and if recording or in mission, also write the voltage to the sensor file
         batt_string = "{}\t{:.2f}".format((datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-',''),battery_volt)
         print("BATT:{}".format(batt_string))
         if (recording or in_mission) and sensor_file.closed == False:
            print("BATT:{}\t{}".format(time.monotonic_ns(), batt_string), file=sensor_file, flush=True)

         #if the battery voltage is critically low, stop all interfaces and initiate a shutdown timeout. The shutdown timeout allows a user to intercept if necessary.
         if battery_volt < 9.0:
            battery_low_counter +=1

            #count to 5 to be sure
            if battery_low_counter >=5:
               logger.debug('Batteries critically low, ending processes now, initiating shutdown in 60 seconds.')
               sys.stdout.flush()

               #end video recording and close the sensor file
               if recording:
                  os.system('echo ca 0 > /var/www/html/FIFO')
                  logger.debug('Ending video capture')
                  sensor_file.close()
               red.stop()

               #indicate shutdown with LEDS: short then long flash repeated
               for x in range (2):
                  red.start(100)
                  sleep(0.1)
                  red.stop()
                  sleep(0.2)
                  red.start(100)
                  sleep(0.4)
                  red.stop()
                  sleep(0.2)
               sleep(battery_low_shutdown_timeout_seconds)

               #actually shutdown
               GPIO.cleanup()
               call("sudo shutdown -h now", shell=True)
               sys.exit()
         else:
            battery_low_counter = 0


      #On the same rotation as SPI, which is way faster, also talk to the IMU on i2c.
      #Get acceleration xyz in Gs, degree per s xyz rotation, micro T magnetic field, and internal temperature.
      if imu_connected and interface_rotation ==3:
         try:
            if imu.dataReady():
               imu.getAgmt()
               imu_string  = "{}\t{:.2f}\t{:.2f}\t{:.2f}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.2f}".format(
                  (datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-',''),
                  imu.axRaw/4096.0, #get Gs, up to +-8G
                  imu.ayRaw/4096.0,
                  imu.azRaw/4096.0,
                  imu.gxRaw/131.0, #get degrees per second, up to +-250d/s
                  imu.gyRaw/131.0,
                  imu.gzRaw/131.0,
                  imu.mxRaw/0.15, #get uT + - 4900uT
                  imu.myRaw/0.15,
                  imu.mzRaw/0.15,
                  (imu.tmpRaw-21)/333.87 + 21) #get temperature in C. All the maths here are inctructions from IMU datasheet

               #print IMU data to console and to any open sensor file.
               print("IMUN:{}".format(imu_string))
               if (recording or in_mission) and sensor_file.closed == False:
                  print("IMUN:{}\t{}".format(time.monotonic_ns(), imu_string), file=sensor_file, flush= True)
         except Exception as e:
            logger.error("@IMUN\n{}".format(e))

      #get keller sensor data
      if keller_connected and interface_rotation ==4:
         #use try except to avoid i2c crash
         try:
            #get the data
            outside.read()

            #approximate depth from pressure. Keller 7LD is rated 3-200bar absolute pressure and reads 1 bar as zero
            #so depth calculation of less than 20M are less accurate
            uncalibrated_depth = outside.pressure()*10
            approx_depth = uncalibrated_depth - keller_depth_offset

            #print keller data to stream and any open sensor file
            kell_string  = "{}\t{:.2f}\t{:.1f}\t{:.2f}".format((datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-',''),outside.pressure(), approx_depth, outside.temperature())
            print("KELL:{}".format(kell_string))
            sys.stdout.flush()
            if (recording or in_mission) and sensor_file.closed == False:
               print("KELL:{}\t{}".format(time.monotonic_ns(),kell_string), file=sensor_file, flush = True)

         except Exception as e:
            logger.error("@KELL\n{}".format(e))
         print('') #print an extra line in console to show one second passed


      #go back to top of the interface rotation
      interface_rotation %= 4


   #after time determined by hdmi_act_led_timeout, disable these perpherals
   #to reduce power consumption (HDMI and ACT LED) and remove light noise (ACT LED)
   if hdmi_enabled == True and (time.time() - hdmi_end_timer > hdmi_act_led_timeout_seconds):
      os.system('/usr/bin/tvservice -o')
      os.system('echo none | sudo tee /sys/class/leds/led0/trigger')
      os.system('echo 0 | sudo tee /sys/class/leds/led0/brightness')
      logger.debug('Timeout elapsed since start. HDMI and ACT LED disabled.')
      hdmi_enabled = False


   #collect raw hall states, use 1 - GPIO, because they are pull up and active low.
   hall_button_last = hall_button_active
   hall_button_active = 1-GPIO.input(8)  #push button
   hall_active[0] = 1-GPIO.input(11)     #wifi mode
   hall_active[1] = 1-GPIO.input(25)     #video mode
   hall_active[2] = 1-GPIO.input(9)      #photo mode
   hall_active[3] = 1-GPIO.input(10)     #mission 1 mode
   hall_active[4] = 1-GPIO.input(24)     #mission 2 mode
   hall_active[5] = 1-GPIO.input(14)     #powerdown signal


   #determine overall overtime confidence in each hall sensor being active
   for x in range(6):
      #if particular hall is active, increase confidence score
      if(hall_active[x] and hall_confidence[x] < 25):
         hall_confidence[x] += 1
      #if particular hall is not active, decrease confidence score
      elif (hall_active[x] == 0 and hall_confidence[x] > 0):
         hall_confidence[x] -= 1


   #pick the mode based on highest hall confidence score that is also over a minimum threshold
   hall_mode_last = hall_mode
   hall_mode = 0
   for x in range(6):
      if (hall_confidence[x] >= 15):
         hall_mode = 1 + x
   #however for special cases such as when currently recording video and or writing to a sensor file
   #go back to that previous mode, setup a flag that it needs to wrap up, and let in correctly end processes
   if ((recording or in_mission) and hall_mode != hall_mode_last) : #and hall_mode != 6 and hall_mode!=2):
      hall_mode = hall_mode_last
      end_processes_mode_changed_flag = 1


####################################################################### MODES
   #No magnet detected, no indication
   if (hall_mode == 0 and hall_mode != hall_mode_last):
      print('No hall detected, doing nothing.')
      sys.stdout.flush()
      red.stop()

      #write status to status file
      with open('/home/pi/git/maka-niu/code/log/status.txt', 'w') as f:
          print("0" , end="", file=f, flush= True)



   #Magnet at Wifi Mode
   if (hall_mode == 1):
      #When initially entering mode: Enable wifi, flash red 3 times, and buzz
      if (hall_mode != hall_mode_last):

         #write status to status file
         with open('/home/pi/git/maka-niu/code/log/status.txt', 'w') as f:
            print("1" , end="", file=f, flush= True)

         #enable wifi
         wifi_enabled = True
         os.system('sudo ifconfig wlan0 up')
         os.system('sudo ifconfig ap@wlan0 up')
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tWifi Mode actvated. three red flashes'.format(time_stamp))

         #haptic feedback and led indication
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

      #in wifi mode, when the button is pressed, flash the green led a number of times based on battery life 1x for low, 2x for mid, 3x for high
      if (hall_button_active != hall_button_last and hall_button_active):
         blink_count = 1
         if battery_volt > 11.2:    #about 100-80% charge
            blink_count=5
         elif battery_volt > 10.8:  #about 80-60% charge
            blink_count=4
         elif battery_volt > 10.4:  #about 60-40% charge
            blink_count=3
         elif battery_volt > 10:    #about 40-20% charge
            blink_count=2
         else:                      #about 20-0% charge. Will initiate shutdown at 9V (3V/cell)
            blink_count=1

         logger.debug('Battery check requested. {} flashes'.format(blink_count))

         for x in range(blink_count):
            green.start(100)
            sleep(0.5)
            green.stop()
            sleep(0.2)



   #Magnet at Video Mode
   if (hall_mode == 2):
      #When initially entering mode: Disable wifi, turn on red led, and buzz
      if (hall_mode != hall_mode_last):

         #write status to status file
         with open('/home/pi/git/maka-niu/code/log/status.txt', 'w') as f:
            print("2" , end="", file=f, flush= True)

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tVideo Mode activated, press button to begin recording'.format(time_stamp))

         #haptic feedback and led indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58) #58, 64, 95 are good choice transition buzzes
            drv.play()
         red.start(100)
         recording = 0

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')


      #if the button is freshly pressed (Here we do not care about continuous press or depress)
      if (hall_button_active != hall_button_last and hall_button_active):

         #If not recording, begin recording.
         if (recording == 0):
            #1st determine time stamp, video file name, and create same named sensor data file
            time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds").replace(':','_').replace('-','_')
            file_name = serial_number + "_" + time_stamp
            with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
               print(file_name , end="", file=f)
            sensor_file = open("/var/www/html/media/{}{}".format(file_name,".txt"), 'w')
            print("DEID:{}\nMACA:{}".format(serial_number,mac_address), file=sensor_file, flush = True)


            #begin video capture via RPi interface
            os.system('echo ca 1 > /var/www/html/FIFO')
            logger.debug('{}\tStarting video capture: {}'.format(time_stamp,file_name))
            recording = 1
            video_started_time = time.time()

            #haptif feedback short buzz and turn off red led
            if haptic_connected:
               drv.stop()
               drv.sequence[0] = adafruit_drv2605.Effect(74) #1
               drv.play()
            red.stop()

         #Or if recording, end recording
         elif (recording):
            #end recordign via RPi interface
            os.system('echo ca 0 > /var/www/html/FIFO')
            time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
            logger.debug('{}\tEnding video capture'.format(time_stamp))

            #cleanup, clear recording flag and close the sensor data file
            recording = 0
            sensor_file.close()

            #haptic feedback short buzz and turn the red led back on
            if haptic_connected:
               drv.stop()
               drv.sequence[0] = adafruit_drv2605.Effect(74) #10 nice double
               drv.play()
            red.start(100)

      #This bit gets executed if the has been moved away from video mode while a recording was active
      if end_processes_mode_changed_flag:
         #end recordign via RPi interface
         os.system('echo ca 0 > /var/www/html/FIFO')
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tLeft Camera mode, ending video capture'.format(time_stamp))

         #cleanup, clear recording flag and close the sensor data file
         recording = 0
         sensor_file.close()
         end_processes_mode_changed_flag = 0

         #there is no LED or haptic feedback in this scenario

      #We are limiting video files to fixed max length segments. If the length reaches the timelimit, stop the recording, and start a new one
      if (recording and (time.time()-video_started_time) > video_timelimit_seconds):
         #end recordign via RPi interface
         os.system('echo ca 0 > /var/www/html/FIFO')
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tVideo capture time limit reached: Start new capture'.format(time_stamp))

         #close the current sensor file and add a short pause for the RPi interface
         sensor_file.close()
         sleep(0.25)

         #determine new time stamp, video file name, and create same named sensor data file
         time_stamp = datetime.datetime.now()+datetime_offset
         file_name = serial_number + "_" + time_stamp.isoformat("_","milliseconds").replace(':','_').replace('-','_')
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(file_name , end="", file=f)
         sensor_file = open("/var/www/html/media/{}{}".format(file_name,".txt"), 'w')
         print("DEID:{}\nMACA:{}".format(serial_number,mac_address), file=sensor_file, flush = True)

         #restart video recording via RPi interace
         os.system('echo ca 1 > /var/www/html/FIFO')
         video_started_time = time.time()


   #Magnet at Picture Mode
   if (hall_mode == 3):
      #When initially entering mode: Disable wifi, flash red led 5 times fast, and buzz
      if (hall_mode != hall_mode_last):

         #write status to status file
         with open('/home/pi/git/maka-niu/code/log/status.txt', 'w') as f:
            print("3" , end="", file=f, flush= True)

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tPicture Mode activated, 5 flashes'.format(time_stamp))

         #haptic feedback and led indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()
         for x in range (5):
            sleep(0.12)
            red.start(100)
            sleep(0.12)
            red.stop()

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')


      #If the button is pressed in photo mode, flash the red led, do a short buzz, and take a photo after the led is turned off
      if (hall_button_active and hall_button_active != hall_button_last):

         #record time in order to time possible photo burst
         photo_burst_time = time.time()
         interfaces_time = 0 #this synchronizes interface updates to happen between photos

         #haptic feedback and led indication
         red.start(100)
         if haptic_connected:
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(74)
            drv.play()
         else:
            sleep(0.12)
         red.stop()

         #determine time stamp and img file name
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds").replace(':','_').replace('-','_')
         file_name = serial_number + "_" + time_stamp
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(file_name , end="", file=f)

         #capture image via RPi interface
         os.system('echo im 1 > /var/www/html/FIFO')
         logger.debug('\n{}\tPhoto capture'.format(time_stamp))


         #also create a same named sensor data file and write into it currently available data, and close it right away
         with open("/var/www/html/media/{}{}".format(file_name,".txt"), 'w') as s:

            print("DEID:{}\nMACA:{}".format(serial_number,mac_address), file=s)
            #GNSS data consdiretarions: Since we update all the peripherals elsewhere anyway, we will write down the last stored sensor data in the img sensor file.
            #That is great for battery voltage and for the Keller data, but it's maybe not so great for gpss data which isnt always fresh or available.
            #so if the fix is super recent, write it in the file as per usual. But if the fix is older than 5 seconds, as would be the case in any underwater dive,
            #we will write the last know location in a special line GNS2: current datetime, fix age in seconds, and coordinates.
            #So.. if super recent fix, write GNSS
            if fix_achieved_this_runtime == True:
               fix_age = time.time() - fix_time_stamp
               #recent fix, write GNSS
               if fix_age < 5.0:
                  print("GNSS:{}\t{}".format(time.monotonic_ns(),gnss_string), file = s )
               #fix exists but is outdated, write GNS2
               else:
                  try:
                     gnss_string_packed = gnss_string.split("\t")
                     time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("\t","milliseconds")
                     print("GNS2:{}\t{}\t{:.1f}\t{}\t{}".format(time.monotonic_ns(),time_stamp.replace(':','').replace('-',''), fix_age, gnss_string_packed[-2][:], gnss_string_packed[-1][:]), file = s)
                  except Exception as e:
                     logger.debug("@GNS2 PHOTO {}\t{}".format(time_stamp, e))
            #and write down the BATT and KELL data, easy and that's gonna be current
            print("BATT:{}\t{}".format(time.monotonic_ns(),batt_string), file = s)
            print("KELL:{}\t{}".format(time.monotonic_ns(),kell_string), file = s)
            print("IMUN:{}\t{}".format(time.monotonic_ns(),imu_string), file=s)



      #If the button is continuing to be pressed, continue to take images
      elif (hall_button_active and (time.time() - photo_burst_time > 0.49)):

         #record time in order to time capture instance in photo burst
         photo_burst_time = time.time()

         #haptic feedback with a click. No LED indication in burst
         if haptic_connected:
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(17) #17 for solid click , 80 for short vib
            drv.play()

         #determine time stamp and filename.
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds").replace(':','_').replace('-','_')
         file_name = serial_number + "_" + time_stamp
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(file_name , end="", file=f)

         #capture image vie RPi interface
         os.system('echo im 1 > /var/www/html/FIFO')
         sys.stdout.flush()
         logger.debug('*')

         #also create a same named sensor data file and write into it currently available data, and close it right away
         with open("/var/www/html/media/{}{}".format(file_name,".txt"), 'w') as s:
            print("DEID:{}\nMACA:{}".format(serial_number,mac_address), file= s)
            #GNSS data consdiretarions: Since we update all the peripherals elsewhere anyway, we will write down the last stored sensor data in the img sensor file.
            #That is great for battery voltage and for the Keller data, but it's maybe not so great for gpss data which isnt always fresh or available.
            #so if the fix is super recent, write it in the file as per usual. But if the fix is older than 5 seconds, as would be the case in any underwater dive,
            # we will write the last know location in is a special line GNS2: current datetime, fix age in seconds, and corrdinates
            # so if super recent fix, write GNSS
            if fix_achieved_this_runtime == True:
               fix_age = time.time() - fix_time_stamp
               #recent fix, write GNSS
               if fix_age < 5.0:
                  print("GNSS:{}\t{}".format(time.monotonic_ns(), gnss_string), file = s )
               #fix exists but is outdated, write GNS2
               else:
                  try:
                     gnss_string_packed = gnss_string.split("\t")
                     time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("\t","milliseconds")
                     print("GNS2:{}\t{}\t{:.1f}\t{}\t{}".format(time.monotonic_ns(), time_stamp.replace(':','').replace('-',''), fix_age, gnss_string_packed[-2][:], gnss_string_packed[-1][:]), file = s)
                  except Exception as e:
                     logger.debug("@GNS2 PHOTO {}\t{}".format(time_stamp, e))
            #and write down the BATT and KELL data, easy and that's gonna be current
            print("BATT:{}\t{}".format(time.monotonic_ns(), batt_string), file = s)
            print("KELL:{}\t{}".format(time.monotonic_ns(), kell_string), file = s)
            print("IMUN:{}\t{}".format(time.monotonic_ns(),imu_string), file=s)


      #THere is a bit of a weird bug, that when the photo command is sent to the RPi interfaces too quickly in succesion, which is the case in burst
      #the RPi interface starts to recod a video as well. Behavior is gone if burst speed is reduced. Very odd, Anyway, to prevent the video to run non stop,
      #whenever the button get's unpressed, let's send a stop recording command
      if (hall_button_active==0 and hall_button_active != hall_button_last):
         os.system('echo ca 0 > /var/www/html/FIFO')
         logger.debug('End video just in case it was started in burst')






   #Magnet at Mission 1
   if (hall_mode == 4):
      #When initially entering mode: Disable wifi, do a long red flash, buzz, and create mission duration sensor data file
      if (hall_mode != hall_mode_last):
         #set flag for mission number
         in_mission = 1

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tMission 1 activated'.format(time_stamp))
         sys.stdout.flush()

         #haptic feedback and LED indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()
         red.start(100)
         sleep(0.75)
         red.stop()

         #At start of mission, determine time stamp, and create a mission sensor datafile.
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds").replace(':','_').replace('-','_')
         file_name = serial_number + "_" + mission1_name + "_" + time_stamp
         sensor_file = open("/var/www/html/media/{}{}".format(file_name,".txt"), 'w')
         print("DEID:{}\nMACA:{}".format(serial_number,mac_address), file=sensor_file, flush = True)


         #write status to status file
         with open('/home/pi/git/maka-niu/code/log/status.txt', 'w') as f:
            print("4 {}.txt".format(file_name) , end="", file=f, flush= True)

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')



     #CODE THAT READS FROM THE MISSION FILE AND TAKES ACTION BASED ON THAT.
     #******************************************************************
     # whenever photo taken:
       # name photo file serial number + mission name + datetime
       # in the sensor data file, write ICAP:datetime \t image_filename
     #whenever video capture is started:
       # name video file serial number + mission name + datetime
       # in the sensor data file, write VCAP:datetime \t video_filename
     #whenever video capture is stopped:
       # write to sensor file VSTP:datetime \t video_filename
     #******************************************************************

      #This executes if the dial was moved away from this mission. Close the sensor file, and terminate video capture.
      if end_processes_mode_changed_flag:
         end_processes_mode_changed_flag = 0
         sensor_file.close()
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tEnding mission 1 by dial'.format(time_stamp))
         in_mission = 0
         if recording:
            os.system('echo ca 0 > /var/www/html/FIFO')
            logger.debug('{}\tEnding video capture within Mission 1'.format(time_stamp))
            sys.stdout.flush()
            recording = 0



   #Magnet at Mission 2 , flash  red then green twice.
   if (hall_mode == 5):
      #When initially entering mode: Disable wifi, do two long red led flashes, and buzz
      if (hall_mode != hall_mode_last):
         #set flag for mission number
         in_mission = 2

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tMission 2 activated'.format(time_stamp))
         sys.stdout.flush()

         #haptic feedback and LED indication
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

         #At start of mission, determine time stamp, and create a mission sensor datafile.
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds").replace(':','_').replace('-','_')
         file_name = serial_number + "_" + mission2_name + "_" + time_stamp
         sensor_file = open("/var/www/html/media/{}{}".format(file_name,".txt"), 'w')
         print("DEID:{}\nMACA:{}".format(serial_number,mac_address), file=sensor_file, flush = True)

         #write status to status file
         with open('/home/pi/git/maka-niu/code/log/status.txt', 'w') as f:
            print("5 {}.txt".format(file_name) , end="", file=f, flush= True)

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')


     #CODE THAT READS A LINE FROM THE MISSION JSON AND TAKEs ACTION BASED ON THAT.
     #******************************************************************
     # whenever photo taken:
       # name photo file serial number + mission name + datetime
       # in the sensor data file, write ICAP:datetime \t image_filename
     #whenever video started:
       # name video file serial number + mission name + datetime
       # in the sensor data file, write VCAP:datetime \t video_filename
     #whenever video stopped:
       # write to sensor file VSTP:datetime \t video_filename
     #******************************************************************

      #This executes if the dial was moved away from this mission. Close the sensor file, and terminate video capture.
      if end_processes_mode_changed_flag:
         end_processes_mode_changed_flag = 0
         sensor_file.close()
         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tEnding mission 2 by dial'.format(time_stamp))
         in_mission = 0
         if recording:
            os.system('echo ca 0 > /var/www/html/FIFO')
            logger.debug('{}\tEnding video capture within Mission 2'.format(time_stamp))
            sys.stdout.flush()
            recording = 0


   #Magnet at Power Off.
   if (hall_mode == 6 and hall_mode != hall_mode_last):
      time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
      logger.debug('{}\tPowerdown activated'.format(time_stamp))
      sys.stdout.flush()

      #write status to status file
      with open('/home/pi/git/maka-niu/code/log/status.txt', 'w') as f:
         print("6", end="", file=f, flush= True)


      #Haptic feedback and LED indication
      if haptic_connected:
         drv.sequence[0] = adafruit_drv2605.Effect(47)
         drv.play()
      red.stop()
      for x in range (2): #2 times short then long flashes
         red.start(100)
         sleep(0.05)
         red.stop()
         sleep(0.1)
         red.start(100)
         sleep(0.2)
         red.stop()
         sleep(0.1)
      #GPIO.cleanup()
      call("sudo shutdown -h now", shell=True)
      sys.exit()



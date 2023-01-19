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
from subprocess import call #, PIPE, Popen
import board
import busio
from kellerLD import KellerLD
import socket
import re, uuid
import pigpio
import wavePWM
from bluedot.btcomm import BluetoothServer
#from gpiozero import CPUTemperature

light_duration = 0
light_request_time = time.time()


def get_cpu_temperature():
   try:
      tFile = open('/sys/class/thermal/thermal_zone0/temp')
      temp = float(tFile.read())/1000.0
      return temp
   except:
      return 0


def data_received(data):
   #print(data)
   #try:
   global light_duration
   light_duration = float(data)
   print(light_duration)
      #camera_module.send("OK: " + light_duration)
   global light_request_time
   light_request_time = time.time()

   #except:
      #light_duration = 0
      #camera_module.send("Sorry, what?")

#############################################################SETUP ERROR AND DEBUG LOGGING
#name of the next log file
LOG_FILENAME = '/home/pi/git/maka-niu/code/log/MakaLED_debug.log'

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
hdmi_act_led_timeout_seconds = 90
battery_low_shutdown_timeout_seconds = 60
light_timelimit_seconds = 900 # 15 minutes


mission1_name = 'M1'
mission2_name = 'M2'
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

#setup the GPIO pin that enables 3.3V regulator in the BMS board that powers GPS, Keller, IMU.
GPIO.setup(18, GPIO.OUT)
GPIO.output(18, GPIO.HIGH) #NOTE: is a mission has long standby time and the peripherals are not needed, one may set this pin low to preserve power
sleep(0.5)

#setup SPI for battery ADC via MCP3002 and a 100K/33K voltage divider on the battery pack voltage
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
battery_low_counter = 0
battery_volt = 12
adc_connected = True
try:
   i2c = busio.I2C(board.SCL, board.SDA)
   result = bytearray(2)

   i2c.readfrom_into(0x4e, result)
   battery_volt = ((result[0] <<8 | result[1]) & 0xFFF) * 0.003223
   #: 3.3Vref / 4095(12bit) * 4(voltage_divide) = 0.003223
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

   sleep(battery_low_shutdown_timeout_seconds)
   GPIO.cleanup()
   call("sudo shutdown -h now", shell=True)
   sys.exit()


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



bluetooth_server_running = False
try:
   camera_module = BluetoothServer(data_received)
   logger.debug("Bluetooth server setup")
   bluetooth_server_running = True
except:
   logger.debug("Bluetooth server fail")



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
light_started_time = time.time() # for limiting video to fixed max lentgh segments
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

gps_connected = False
haptic_connected = False

#setup keller depth offset calibration
approx_depth = 0
keller_depth_offset = 0
if os.path.exists('/home/pi/git/maka-niu/code/log/keller_offset.txt'):
   k = open('/home/pi/git/maka-niu/code/log/keller_offset.txt', 'r')
   depth_string = k.readline()
   keller_depth_offset = float(depth_string)
   k.close()
   logger.debug('Initial keller depth offset of {} loaded.'.format(keller_depth_offset))


#Print to stream that setup is over
logger.debug('Maka LED Program setup complete Entering main forever loop.')


pi=pigpio.pi()
light = wavePWM.PWM(pi)
light.set_frequency(1000)

target_brightness = 0
duty_cycle = target_brightness
light.set_pulse_length_in_fraction(13, duty_cycle)
light.update()


#light.cancel()
#pi.stop()
#exit(0)


################################################################# MAIN FOREVER LOOP
while True:
   #short delay to run at 100hz(actually likely much less due to all the other operations.)
   sleep(0.01)
   #disable green led that gets turned on every second if gps has a fix, this creates a 1 hz green indicator of fix.
   #green.stop()

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
    #                 green.start(100)

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
                           keller_depth_offset = keller_depth_offset*0.99 + approx_depth*0.01
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

         i2c.readfrom_into(0x4e, result)
         battery_volt = ((result[0] <<8 | result[1]) & 0xFFF) * 0.003223

         #reading = getBatteryVoltage()
         #if reading < 15 and reading > 5:
         #   battery_volt = battery_volt*0.9 + reading*0.1





         #print voltage to stream, and if recording or in mission, also write the voltage to the sensor file
         batt_string = "{}\t{:.2f}".format((datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-',''),battery_volt)
         print("HARD:{}\t{}".format(batt_string, get_cpu_temperature()))

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
     #          red.stop()

               #indicate shutdown with LEDS: short then long flash repeated
               for x in range (2):
      #            red.start(100)
                  sleep(0.1)
       #           red.stop()
                  sleep(0.2)
        #          red.start(100)
                  sleep(0.4)
         #         red.stop()
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
            approx_depth = outside.pressure()*10 - keller_depth_offset

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



   duty_cycle = duty_cycle*0.98 + target_brightness*0.02
   light.set_pulse_length_in_fraction(13, duty_cycle)
   light.update()



####################################################################### MODES
   #No magnet detected, no indication
   if (hall_mode == 0 and hall_mode != hall_mode_last):
      print('No hall detected, doing nothing.')
      sys.stdout.flush()
      #red.stop()

      target_brightness = 0.0

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
            duty_cycle = 0.02
            light.set_pulse_length_in_fraction(13, duty_cycle)
            light.update()

            sleep(0.2)
            duty_cycle = 0.0
            light.set_pulse_length_in_fraction(13, duty_cycle)
            light.update()

         target_brightness = 0.0

         if haptic_connected:
            drv.stop()

      if bluetooth_server_running:
         if (time.time() - light_request_time) < light_duration:
            target_brightness = 0.5
            #light.set_pulse_length_in_fraction(13, 0.5)
            #light.update()
         else:
            target_brightness = 0.0
            #logger.debug('*')
            #light.set_pulse_length_in_fraction(13, 0.0)
            #light.update()


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
            duty_cycle = 0.02
            light.set_pulse_length_in_fraction(13, duty_cycle)
            light.update()

            sleep(0.5)
            duty_cycle = 0.0
            light.set_pulse_length_in_fraction(13, duty_cycle)
            light.update()

            sleep(0.5)


   #Magnet at Brightness 1
   if (hall_mode == 2):
      #When initially entering mode: Disable wifi, do a long red flash, buzz, and create mission duration sensor data file
      if (hall_mode != hall_mode_last):

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tBrightness 1 activated'.format(time_stamp))
         sys.stdout.flush()

         target_brightness = .125

         #haptic feedback and LED indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')

   #Magnet at Brightness 2
   if (hall_mode == 3):
      #When initially entering mode: Disable wifi, do a long red flash, buzz, and create mission duration sensor data file
      if (hall_mode != hall_mode_last):

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tBrightness 2 activated'.format(time_stamp))
         sys.stdout.flush()

         target_brightness = .250

         #haptic feedback and LED indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')

   #Magnet at Brightness 3
   if (hall_mode == 4):
      #When initially entering mode: Disable wifi, do a long red flash, buzz, and create mission duration sensor data file
      if (hall_mode != hall_mode_last):

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tBrightness 3 activated'.format(time_stamp))
         sys.stdout.flush()

         target_brightness = .500

         #haptic feedback and LED indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')

   #Magnet at Brightness 4
   if (hall_mode == 5):
      #When initially entering mode: Disable wifi, do a long red flash, buzz, and create mission duration sensor data file
      if (hall_mode != hall_mode_last):

         time_stamp = (datetime.datetime.now()+datetime_offset).isoformat("_","milliseconds")
         logger.debug('{}\tBrightness 4 activated'.format(time_stamp))
         sys.stdout.flush()

         target_brightness = .99

         #haptic feedback and LED indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()

      #In this mode, if Maka Niu is underwater, diable wifi to save batteries
      #This way, on land, users can connect to wifi and live stream if desired
      if (wifi_enabled == True and (fix_is_live == False and approx_depth > 1)):
         wifi_enabled = False
         os.system('sudo ifconfig wlan0 down')
         os.system('sudo ifconfig ap@wlan0 down')


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
      #red.stop()
      #for x in range (2): #2 times short then long flashes
         #red.start(100)
         #sleep(0.05)
         #red.stop()
         #sleep(0.1)
         #red.start(100)
         #sleep(0.2)
         #red.stop()
         #sleep(0.1)
      #GPIO.cleanup()
      for x in range(2):
         duty_cycle = 0.02
         light.set_pulse_length_in_fraction(13, duty_cycle)
         light.update()
         sleep(0.05)

         duty_cycle = 0.0
         light.set_pulse_length_in_fraction(13, duty_cycle)
         light.update()
         sleep(0.1)

         duty_cycle = 0.02
         light.set_pulse_length_in_fraction(13, duty_cycle)
         light.update()
         sleep(0.2)

         duty_cycle = 0.0
         light.set_pulse_length_in_fraction(13, duty_cycle)
         light.update()
         sleep(0.1)
      light.cancel()
      pi.stop()


      call("sudo shutdown -h now", shell=True)
      sys.exit()



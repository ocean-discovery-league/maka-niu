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
#control variables: change these as desired
serial_number= "MKN0001"
mission1_name = "M1" #can be user specified
mission2_name = "M2" #can be user specified
hdmi_act_led_timeout_seconds = 90
battery_low_shutdown_timeout_seconds = 60
video_timelimit_seconds = 900 # 15 minutes


#To avoid messing with pi's clock, we are creating a UTC datetime offset variable that will be used for timestamping filenames and sensor data
datetime_offset = datetime.timedelta(0)
print(datetime.datetime.now())

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
   print("Starting battery voltage:" , round(battery_volt,3), "V")
except:
   print("ADC not connected, SPI fail")
   adc_connected = False

if battery_volt < 5 or battery_volt > 15:
   print("ADC not connected, values out of range.")
   adc_connected = False
   battery_volt = 12

#If the batteries are already depleted at start of runtime, initiate shutdown with a timeout to allow for user to intercept
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
   drv.sequence[0] = adafruit_drv2605.Effect(58) #58 is solif buzz
   drv.play()
except:
   print("Haptic feedback not connected.")
   haptic_connected = False

#setup i2c for GPS
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
gps = qwiic_titan_gps.QwiicTitanGps()
gps_connected = True
if gps.connected is False:
   gps_connected = False
   print("GPS device not connected.", file = sys.stderr)
gps.begin()


#setup i2c for keller pressure/temperature sensor
#If there is a hardware issue, flag it and do not use the feature anymore this runtime.
outside = KellerLD()
keller_connected = True
try:
   outside.init()
except:
   keller_connected = False
   print("Keller LD sensor not connected.")

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
fix_latitude = 0.0
fix_longitude = 0.0
fix_last_UTC_update = datetime.datetime.now()
gnss_string = ""
batt_string = ""
kell_string = ""

#If all the hardware interfaces appear to be functioning, turn the green len on for 3 seconds
if adc_connected and gps_connected and keller_connected:
   print('ADC, GPS, and Keller hardware all talking.')
   green.start(100)
   sleep(3)
red.stop()
green.stop()

#Print to stream that setup is over
print('Maka Niu Program iniated. Entering main forever loop.')
sys.stdout.flush()


################################################################# MAIN FOREVER LOOP
while True:
   #short delay to run at 100hz(actually likely much less due to all the other operations.)
   sleep(0.01)
   #disable green led that gets turned on every second if gps has a fix, this creates a 1 hz green indicator of fix.
   green.stop()

   #every second, update GPS data, battery info, and pressure/temp info. Rotate through tasks to minimize time gaps
   if (time.time() - interfaces_time) > 0.25:
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
                     green.start(100)

                     #check that the date time stamps are in valid format, sometimes they are not. If ok, update the local UTC timestamp offset
                     if isinstance(gps.gnss_messages["Date"], datetime.date) and isinstance(gps.gnss_messages["Time"], datetime.time):

                        #if both date and tiem data is good, combine them into one datetime object
                        datetime_gps = datetime.datetime.combine(gps.gnss_messages["Date"],gps.gnss_messages["Time"]).replace(microsecond = 0)

                        #sometimes the gps gives back the same time multiple times, so only currec the UTC datetime if it a new number
                        if fix_last_UTC_update != datetime_gps:
                           datetime_offset = datetime_gps - datetime.datetime.now()
                           fix_last_UTC_update = datetime_gps

                        #check that the latitude and longitude appear to be in valid format, sometimes they are not.
                        if isinstance(gps.gnss_messages["Latitude"],float) and isinstance(gps.gnss_messages["Longitude"],float):

                           #Now we are confident in both time and location
                           #record the pi time at time of good fix as well as the new longitude and latitude
                           fix_achieved_this_runtime = True
                           fix_time_stamp = time.time() #this number is for calculating fix age later for photos.
                           fix_latitude = gps.gnss_messages["Latitude"]
                           fix_longitude = gps.gnss_messages["Longitude"]

                           #If data looks valid, print GPS data to stream and to any open sensor file.
                           gnss_string = "{}\t{:.7f}\t{:.7f}".format(
                              (datetime.datetime.now() + datetime_offset).isoformat(sep='\t', timespec = 'milliseconds').replace(':', '').replace('-', ''),
                              gps.gnss_messages["Latitude"],
                              gps.gnss_messages["Longitude"])
                           print("GNSS:{}".format(gnss_string))
                           if (recording or in_mission) and sensor_file.closed == False:
                              print("GNSS:{}\t{}".format(time.monotonic_ns(),gnss_string), file=sensor_file)

         except Exception as e:
            print(e)

      #get battery voltage ADC via SPI interface, dont update during photo burst
      elif adc_connected and interface_rotation == 2: # and hall_button_active ==0:

         #Get the adc and then since it is a bit noisy, apply a running average
         reading = getBatteryVoltage()
         if reading < 15 and reading > 5:
            battery_volt = battery_volt*0.9 + reading*0.1

         #print voltage to stream, and if recording or in mission, also write the voltage to the sensor file
         batt_string = "{}\t{:.2f}".format((datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-',''),battery_volt)
         print("BATT:{}".format(batt_string))
         if (recording or in_mission) and sensor_file.closed == False:
            print("BATT:{}\t{}".format(time.monotonic_ns(), batt_string), file=sensor_file)

         #if the battery voltage is critically low, stop all interfaces and initiate a shutdown timeout. The shutdown timeout allows a user to intercept if necessary.
         if battery_volt < 9.0:
            battery_low_counter +=1

            #count to 5 to be sure
            if battery_low_counter >=5:
               print('Batteries critically low, ending processes now, initiating shutdown in 60 seconds.')
               sys.stdout.flush()

               #end video recording and close the sensor file
               if recording:
                  os.system('echo ca 0 > /var/www/html/FIFO')
                  print('Ending video capture')
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

      #get keller sensor data
      elif keller_connected and interface_rotation ==3:
         #use try except to avoid i2c crash
         try:
            #get the data
            outside.read()

            #approximate depth from pressure. Keller 7LD is rated 3-200bar
            #so depth calculation of less than 20M are propbaly junk, but keep
            approx_depth = outside.pressure()*10-10

            #print keller data to stream and any open sensor file
            kell_string  = "{}\t{:.2f}\t{:.1f}\t{:.2f}".format((datetime.datetime.now()+ datetime_offset).isoformat(sep='\t',timespec='milliseconds').replace(':','').replace('-',''),outside.pressure(), approx_depth, outside.temperature())
            print("KELL:{}".format(kell_string))
            sys.stdout.flush()
            if (recording or in_mission) and sensor_file.closed == False:
               print("KELL:{}\t{}".format(time.monotonic_ns(),kell_string), file=sensor_file)

         except Exception as e:
            print(e)


      #just print a new line every second
      elif interface_rotation ==4:
         print('')

      #got back to top of the interface rotation
      interface_rotation %= 4

   #after time determined by hdmi_act_led_timeout, disable these perpherals
   #to reduce power consumption (HDMI and ACT LED) and remove light noise (ACT LED)
   if hdmi_enabled == True and (time.time() - hdmi_end_timer > hdmi_act_led_timeout_seconds):
      os.system('/usr/bin/tvservice -o')
      os.system('echo none | sudo tee /sys/class/leds/led0/trigger')
      os.system('echo 0 | sudo tee /sys/class/leds/led0/brightness')
      print('Timeout elapsed since start. HDMI and ACT LED disabled.')
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
   #however for special cases such as when currently recording,
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

   #Magnet at Wifi Mode
   if (hall_mode == 1):
      #When initially entering mode: Enable wifi, flash red 3 times, and buzz
      if (hall_mode != hall_mode_last):
         os.system('sudo ifconfig wlan0 up')
         print('Wifi Mode actvated. three red flashes')
         sys.stdout.flush()

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

   #Magnet at Video Mode
   if (hall_mode == 2):
      #When initially entering mode: Disable wifi, turn on red led, and buzz
      if (hall_mode != hall_mode_last):
         #os.system('sudo ifconfig wlan0 down')
         print('Video Mode activated, press button to begin recording')
         sys.stdout.flush()

         #haptic feedback and led indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58) #58, 64, 95 are good choice transition buzzes
            drv.play()
         red.start(100)
         recording = 0

      #if the button is freshly pressed (Here we do not care about continuous press or depress)
      if (hall_button_active != hall_button_last and hall_button_active):

         #If not recording, begin recording.
         if (recording == 0):
            #1st determine time stamp, video file name, and create same named sensor data file
            time_stamp = datetime.datetime.now()+datetime_offset
            filename = serial_number + "_" + time_stamp.isoformat("_","milliseconds")
            with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
               print(filename , end="", file=f)
            sensor_file = open("/var/www/html/media/{}{}".format(filename,".txt"), 'w')

            #begin video capture via RPi interface
            os.system('echo ca 1 > /var/www/html/FIFO')
            print('Starting video capture')
            sys.stdout.flush()
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
            print('Ending video capture')
            sys.stdout.flush()

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
         print('Left Camera mode, ending video capture')
         sys.stdout.flush()

         #cleanup, clear recording flag and close the sensor data file
         recording = 0
         sensor_file.close()
         end_processes_mode_changed_flag = 0

         #there is no LED or haptic feedback in this scenario

      #We are limiting video files to fixed max length segments. If the length reaches the timelimit, stop the recording, and start a new one
      if (recording and (time.time()-video_started_time) > video_timelimit_seconds):
         #end recordign via RPi interface
         os.system('echo ca 0 > /var/www/html/FIFO')
         print('Video capture time limit reached: Start new capture')
         sys.stdout.flush()

         #close the current sensor file and add a short pause for the RPi interface
         sensor_file.close()
         sleep(0.25)

         #determine new time stamp, video file name, and create same named sensor data file
         time_stamp = datetime.datetime.now()+datetime_offset
         filename = serial_number + "_" + time_stamp.isoformat("_","milliseconds")
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(filename , end="", file=f)
         sensor_file = open("/var/www/html/media/{}{}".format(filename,".txt"), 'w')

         #restart video recording via RPi interace
         os.system('echo ca 1 > /var/www/html/FIFO')
         sys.stdout.flush()
         video_started_time = time.time()


   #Magnet at Picture Mode
   if (hall_mode == 3):
      #When initially entering mode: Disable wifi, flash red led 5 times fast, and buzz
      if (hall_mode != hall_mode_last):
         #os.system('sudo ifconfig wlan0 down')
         print('Picture Mode activated, 5 flashes. Press button to capture image, hold for burst')
         sys.stdout.flush()

         #haptic feedback and led indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()
         for x in range (5):
            sleep(0.12)
            red.start(100)
            sleep(0.12)
            red.stop()

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
#         sleep(0.05)
         red.stop()

         #determine time stamp and img file name
         time_stamp = datetime.datetime.now()+datetime_offset
         filename = serial_number + "_" + time_stamp.isoformat("_","milliseconds")
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(filename , end="", file=f)

         #capture image via RPi interface
         os.system('echo im 1 > /var/www/html/FIFO')
         print('\nPhoto capture')
         sys.stdout.flush()


         #also create a same named sensor data file and write into it currently available data, and close it right away
         with open("/var/www/html/media/{}{}".format(filename,".txt"), 'w') as s:
            #GNSS data consdiretarions: Since we update all the peripherals elsewhere anyway, we will write down the last stored sensor data in the img sensor file.
            #That is great for battery voltage and for the Keller data, but it's maybe not so great for gpss data which isnt always fresh or available.
            #so if the fix is super recent, write it in the file as per usual. But if the fix is older than 5 seconds, as would be the case in any underwater dive,
            # we will write the last know location in is a special line GNS2: current datetime, fix age in seconds, and corrdinates
            # so if super recent fix, write GNSS
            if fix_achieved_this_runtime == True:
               fix_age = time.time() - fix_time_stamp
               #recent fix, write GNSS
               if fix_age < 5.0:
                  print("GNSS:{}\t{}".format(time.monotonic_ns(),gnss_string), file = s )
               #fix exists but is outdated, write GNS2
               else:
                  try:
                     gnss_string_packed = gnss_string.split("\t")
                     print("GNS2:{}\t{}\t{:.1f}\t{}\t{}".format(time.monotonic_ns(),time_stamp.isoformat("\t","milliseconds").replace(':','').replace('-',''), fix_age, gnss_string_packed[-2][:], gnss_string_packed[-1][:]), file = s)
                  except Exception as e:
                     print(e)
            #and write down the BATT and KELL data, easy and that's gonna be current
            print("BATT:{}\t{}".format(time.monotonic_ns(),batt_string), file = s)
            print("KELL:{}\t{}".format(time.monotonic_ns(),kell_string), file = s)



      #If the button is continuing to be pressed, continue to take images
      elif (hall_button_active and (time.time() - photo_burst_time > 0.25)):

         #record time in order to time capture instance in photo burst
         photo_burst_time = time.time()

         #haptic feedback with a click. No LED indication in burst
         if haptic_connected:
            drv.stop()
            drv.sequence[0] = adafruit_drv2605.Effect(17) #17 for solid click , 80 for short vib
            drv.play()

         #determine time stamp and filename.
         time_stamp = datetime.datetime.now()+datetime_offset
         filename = serial_number + "_" + time_stamp.isoformat("_","milliseconds")
         with open('/dev/shm/mjpeg/user_annotate.txt', 'w') as f:
            print(serial_number,time_stamp.isoformat("_","milliseconds"), sep ='_' , end="", file=f)

         #capture image vie RPi interface
         os.system('echo im 1 > /var/www/html/FIFO')
         print('*')
         sys.stdout.flush()

         #also create a same named sensor data file and write into it currently available data, and close it right away
         with open("/var/www/html/media/{}{}".format(filename,".txt"), 'w') as s:
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
                     print("GNS2:{}\t{}\t{:.1f}\t{}\t{}".format(time.monotonic_ns(), time_stamp.isoformat("\t","milliseconds").replace(':','').replace('-',''), fix_age, gnss_string_packed[-2][:], gnss_string_packed[-1][:]), file = s)
                  except Exception as e:
                     print(e)
            #and write down the BATT and KELL data, easy and that's gonna be current
            print("BATT:{}\t{}".format(time.monotonic_ns(), batt_string), file = s)
            print("KELL:{}\t{}".format(time.monotonic_ns(), kell_string), file = s)


      #THere is a bit of a weird bug, that when the photo command is sent to the RPi interfaces too quickly in succesion, which is the case in burst
      #the RPi interface starts to recod a video as well. Behavior is gone if burst speed is reduced. Very odd, Anyway, to prevent the video to run non stop,
      #whenever the button get's unpressed, let's send a stop recording command
      if (hall_button_active==0 and hall_button_active != hall_button_last):
         os.system('echo ca 0 > /var/www/html/FIFO')







   #Magnet at Mission 1
   if (hall_mode == 4):
      #When initially entering mode: Disable wifi, do a long red flash, buzz, and create mission duration sensor data file
      if (hall_mode != hall_mode_last):
         #set flag for mission number
         in_mission = 1

         #disable wifi
         #os.system('sudo ifconfig wlan0 down')
         print('Mission 1 activated')
         sys.stdout.flush()

         #haptic feedback and LED indication
         if haptic_connected:
            drv.sequence[0] = adafruit_drv2605.Effect(58)
            drv.play()
         red.start(100)
         sleep(0.75)
         red.stop()

         #At start of mission, determine time stamp, and create a mission sensor datafile.
         time_stamp = datetime.datetime.now()+datetime_offset
         filename = serial_number + "_" + mission1_name + "_" + time_stamp.isoformat("_","milliseconds")
         sensor_file = open("/var/www/html/media/{}{}".format(filename,".txt"), 'w')

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
         print('Ending mission 1 by dial')
         in_mission = 0
         if recording:
            os.system('echo ca 0 > /var/www/html/FIFO')
            print('Ending video capture within Mission 1')
            sys.stdout.flush()
            recording = 0



   #Magnet at Mission 2 , flash  red then green twice.
   if (hall_mode == 5):
      #When initially entering mode: Disable wifi, do two long red led flashes, and buzz
      if (hall_mode != hall_mode_last):
         #set flag for mission number
         in_mission = 2

         #disable wifi
         #os.system('sudo ifconfig wlan0 down')
         print('Mission 2 activated')
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
         time_stamp = datetime.datetime.now()+datetime_offset
         filename = serial_number + "_" + mission2_name + "_" + time_stamp.isoformat("_","milliseconds")
         sensor_file = open("/var/www/html/media/{}{}".format(filename,".txt"), 'w')

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
         print('Ending mission 2 by dial')
         in_mission = 0
         if recording:
            os.system('echo ca 0 > /var/www/html/FIFO')
            print('Ending video capture within Mission 2')
            sys.stdout.flush()
            recording = 0


   #Magnet at Power Off.
   if (hall_mode == 6 and hall_mode != hall_mode_last):
      print('Powerdown activated')
      sys.stdout.flush()

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


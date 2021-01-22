#!/usr/bin/python
#import time
from time import sleep
#import os
#import array as arr
#import sys
#from subprocess import call
import spidev
#from gpiozero import MCP3002


############################################################### SETUP
#setup timer for videos
spi_ch = 2
spi = spidev.SpiDev(1, spi_ch)
spi.max_speed_hz = 120000

def read_adc(adc_ch, vref = 3.3):

   if adc_ch != 0:
      adc_ch = 1

   msg = 0b11
   msg = ((msg << 1) + adc_ch) << 5
   msg = [msg, 0b00000000]
   reply = spi.xfer2(msg)

   adc = 0
   for n in reply:
      adc = (adc << 8) + n

   adc = adc >> 1

   voltage = (vref * adc ) /1024

   return voltage

try:
   while True:
      adc_0 = read_adc(0)
      print("Ch 0:", round(adc_0,2),  "V Ch 1:", round(adc_1,2), "V")
      sleep(0.2)
#MCP3002(channel=2, device=1)
finally:
   print('Test Spi.')




################################################################# MAIN FOREVER LOOP
#while True:
 # sleep(3)

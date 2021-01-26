#!/usr/bin/env python
#-----------------------------------------------------------------------------
# INTRO BY LUI KAWASUMI
# This example code is baded 99% on a Spakfun Example for SparkFun GPS Breakout - XA1110
# The XA1110 was based on the Titan X gps module, hence calls and references to the titan.
# The XM1110 is similar enough and has same i2c address as XA1110 and that why we can use this.
# When you run this example, a warnign will print about i2c stretching.
# It appers we need not heed this warnin with the XM1110. Perhaps hardware has sped up.
# Sometimes you will get blank data, i dont think that is i2c related but could be. LUI OUT
#-----------------------------------------------------------------------------
#
# In this example, much like the first, NMEA data is requested from the SparkFun
# GPS Breakout Board. All data that is retrieved is the printed to the screen.
#------------------------------------------------------------------------
#
# Written by  SparkFun Electronics, October 2019
#
#
# More information on qwiic is at https://www.sparkfun.com/qwiic
#
# Do you like this library? Help support SparkFun. Buy a board!
#
#==================================================================================
# Copyright (c) 2019 SparkFun Electronics
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#==================================================================================
#

from __future__ import print_function
from time import sleep
import sys
import qwiic_titan_gps

def run_example():

	print("Example code for XM1110, based on SparkFun GPS Breakout - XA1110")
	qwiicGPS = qwiic_titan_gps.QwiicTitanGps()

	if qwiicGPS.connected is False:
		print("Could not connect to to the GPS Unit. Double check that it's wired correctly.", file=sys.stderr)
		return

	qwiicGPS.begin()

	while True:
		if qwiicGPS.get_nmea_data() is True:
            	#access specific items by name like this, lui
			print("UTC time: {}, latitude: {} longitude: {}".format(
				qwiicGPS.gnss_messages["Time"],
				qwiicGPS.gnss_messages["Latitude"],
				qwiicGPS.gnss_messages["Longitude"],))

		#or to print everything, use this, lui
		for k,v in qwiicGPS.gnss_messages.items():
                	print(k, ":", v)
		print('\n')
		sleep(1.0) #GPSS refreshes/reloads the i2c buffer once a second, so do not request data in less time. lui

if __name__ == '__main__':
	try:
		run_example()
	except (KeyboardInterrupt, SystemExit) as exErr:
		print("Ending Basic Example.")
	sys.exit(0)

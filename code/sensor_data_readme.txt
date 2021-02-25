This document serves as a key for MakaNiu's recorded sensor data files. Each line contains all available data from a single sensor. The general format is as follows:
4 letter code indicating the data source / nanosecond runtime of the pi computer / UTC date / UTC time/ data 1 / data 2 / ... / etc  
At time of this writing, 4 main codes are in use, but the format is designed to allow for future expansion of sensors. The current codes are GNSS, BATT, IMUN, KELL


************** GNSS 
GNSS stands for Global Navigation Satellite System. 
There are two data entries latitude and longitude. 
Note that MakaNiu also uses this source to get UTC time, 
which is then used to timestamp all other sensor data.
The GNSS signal is not always available, and at those times, the line is not written.
(Also see note for alternate code GNS2 at bottom of code list)
Example:
GNSS:161753520979	20210222	170359.012	42.3592682	-71.1121308


************** BATT 
BATT stands for Battery voltage. 
There is one data entry and that is the voltage of the 3 cell li-ion battery pack.
12.6V is the absolute maximum charge, and at 9 volts MakaNiu is programmed to shut down.
Example:
BATT:161883566693	20210222	170359.147	10.03


************** IMUN 
IMUN stands for Inertial Measurement Unit. 
There are a total of 10 data entries. 
The first three entries are acceleration in G’s in x y and z directions, in that order.
The second set of three are rotation in degree per second along the x y and z axes.
The 3rd set of three are magnetic field strengths in uT (microTesla) in the x y and z directions. 
The final tenth value is the internal temperature of MakaNiu, or more specifically the die temperature of the inertial measurement unit in Celsius. 
For orientation, the z-axis is in line with the cylindrical axis of the camera. When the camera points down, the G value in the Z direction is ~ positive 1.
The y-axis is in line with the trigger button. When the camera is oriented horizontal and the button is top side, the G value in the y direction is ~ positive 1.
For the x direction, rolling the camera to its left side (as if an animal laying on its left side) results in a G value that is ~ positive 1. 
Example:
IMUN:162140432129	20210222	170359.400	-0.23	-0.21	-1.15	-39.4	29.0	18.4	3313.3	-2146.7	-553.3	35.07


************** KELL 
KELL stands for Keller pressure sensor.  
There are a total of 3 data entries.
The 1st entry is pressure in bars. Note that this sensor treats 1 atmospheric bar at the surface of the water as 0 bar. 
The second entry is depth estimation from the pressure. It is bars multiplied by 10, therefore a pressure reading of 1bar leads to a depth estimation of 10 meters. This value is not given by the sensor, it is calculated by the pi.
The third entry is the temperature of the surrounding water in Celsius.
Example:
KELL:162390187667	20210222	170359.652	0.01	0.1	22.70



Additional codes
************** GNS2 
GNS2 is a special version of the GNSS code. It is written at the beginning of photo capture and video capture sensor files if and only if current GNSS data is not available,
but a location fix was achieved at some point during this runtime. This is so that images and videos taken during a dive (but not as part of a mission program) have a location associated with them, 
even though the camera cannot retrieve that information live at time of capture. Therefore, GNS2 data must be treated differently from GNSS data.
The GNS2 line has three data entries. 
The first entry is the time in seconds since the last location update from satellites. The greater this number, the less reliable the data
The second and third entries are latitude and longitude.  
Example:
GNS2:161753520979	20210222	170359.012	21.6	42.3592682	-71.1121308




Below is a short sample of a few seconds of a typical sensor data file:

GNSS:161753520979	20210222	170359.012	42.3592682	-71.1121308
BATT:161883566693	20210222	170359.147	10.03
IMUN:162140432129	20210222	170359.400	-0.23	-0.21	-1.15	-39.4	29.0	18.4	3313.3	-2146.7	-553.3	35.07
KELL:162390187667	20210222	170359.652	0.01	0.1	22.70
GNSS:162724467044	20210222	170359.983	42.3593454	-71.1120747
BATT:162868440360	20210222	170400.131	10.03
IMUN:163124978486	20210222	170400.383	-0.26	0.30	-0.82	42.5	-22.3	132.6	2546.7	-2126.7	-506.7	35.41
KELL:163372094398	20210222	170400.635	0.01	0.1	22.75
GNSS:163696142465	20210222	170400.959	42.3593769	-71.1120356
BATT:163846905823	20210222	170401.110	10.03
IMUN:164103463835	20210222	170401.362	-0.44	-1.01	-1.04	35.7	-20.6	-194.8	2566.7	-2660.0	-633.3	35.07
KELL:164349934637	20210222	170401.613	0.00	0.0	22.70
GNSS:164668889487	20210222	170401.929	42.3593769	-71.1120356
BATT:164835618022	20210222	170402.097	10.03
IMUN:165091523913	20210222	170402.346	-0.23	-0.78	-0.42	-17.8	-59.3	-77.1	4420.0	-3200.0	626.7	35.36
KELL:165335171574	20210222	170402.595	0.00	0.0	22.70
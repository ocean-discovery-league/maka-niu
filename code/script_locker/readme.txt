The scripts in this folder need to be copied to the following destinations if those files are outdated. 
This would be the case for fresh operating systems, or if the scripts them selves are revised.

Use sudo cp to get to replace the following files:

(to setup auto start of the main python script along with error dumping)
/etc/rc.local

(to avoid leftover flags from boxing)
/var/www/html/macros/startstopX.sh

(To enable ic2 and spi)
/boot/config.txt

(To give python control of image and video filenames) 
/var/www/html/raspimjpeg

(With new pi zero 2 w, to library error when running python script)
/usr/local/lib/python3.7/dist-packages/adafruit_platformdetect/constants/boards.py

#!/usr/bin/python
import time
from time import sleep
import os
import array as arr
import sys
from subprocess import call

############################################################### SETUP
#setup timer for videos
video_started_time = time.time()
print('Just Film Python Program Started.')
os.system('echo ca 1 > /var/www/html/FIFO')
print('Starting video capture now')
sys.stdout.flush()

################################################################# MAIN FOREVER LOOP
while True:
   sleep(0.01)
   if ((time.time()-video_started_time) > 899):
         os.system('echo ca 0 > /var/www/html/FIFO')
         print('Video capture time limit reached: Start new capture')
         sys.stdout.flush()
         sleep(0.5)
         os.system('echo ca 1 > /var/www/html/FIFO')
         sys.stdout.flush()
         video_started_time = time.time()

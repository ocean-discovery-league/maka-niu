#!/bin/bash
# This script will move each file in this folder to their target destination.
# Use with caution
#


echo moving startstopX.sh
sudo cp startstopX.sh /var/www/html/macros/startstopX.sh
echo done

echo moving rc.local
sudo cp rc.local_LED /etc/rc.local
echo done

echo moving config.txt
sudo cp config.txt /boot/config.txt
echo done

echo moving board.py
sudo cp boards.py /usr/local/lib/python3.7/dist-packages/adafruit_platformdetect/constants/boards.py
echo done

echo moving raspimjpeg to the macros folder
sudo cp raspimjpeg /var/www/html/raspimjpeg
echo done

echo moving dnsmasq.conf LED version to the etc folder to determine static ip
sudo cp dnsmasq_LED.conf /etc/dnsmasq.conf
echo done

echo moving dhcpcd.conf LED version to the etc folder to determine static ip
sudo cp dhcpcd_LED.conf /etc/dhcpcd.conf
echo done





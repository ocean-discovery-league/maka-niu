#!/bin/bash
# This script will move each file in this folder to their target destination.
# Use with caution
#


echo moving startstopX.sh
sudo cp startstopX.sh /var/www/html/macros/startstopX.sh
sudo cp startstopX.sh /var/www/html/macros/startstop.sh
echo done

echo moving rc.local
sudo cp rc.local /etc/rc.local
echo done

echo moving config.txt
sudo cp config.txt /boot/config.txt
echo done

echo moving boards.py
sudo cp boards.py /usr/local/lib/python3.7/dist-packages/adafruit_platformdetect/constants/boards.py
echo done

echo moving raspimjpeg to the macros folder
sudo cp raspimjpeg /var/www/html/raspimjpeg
echo done

echo moving dnsmasq.conf, that gives statics ip to the etc folder
sudo cp dnsmasq.conf /etc/dnsmasq.conf
echo done

echo moving dhcpcd.conf, that also gives statics ip to the etc folder
sudo cp dhcpcd.conf /etc/dhcpcd.conf
echo done





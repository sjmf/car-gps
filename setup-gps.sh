#!/bin/bash
cd "$(dirname "$0")"
# Set up Adafruit Ultimate GPS on the GPIO serial UART

if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root"; exit 1;
fi

if [ ! -c /dev/ttyAMA0 ]; then
    echo "UART not found. You should run `sudo raspi-config`, and"
    echo "select 'Advanced Options' -> 'A8 Serial', then disable"
    echo "the on-boot serial connection of the rPi."
    exit 1
fi

echo "Setting correct BAUD rate"
stty -F /dev/ttyAMA0 9600
if ! grep -q uart_baud /boot/config.txt; then
    echo "Adding init uart baud rate to /boot/config.txt"
    echo "init_uart_baud=9600" >> /boot/config.txt
fi

echo "Updating sources..."
apt-get update >/dev/null
apt-get install -y gpsd gpsd-clients python-gps
pip install stomp.py

echo "Copying config for UART connection"
cp -v config/gpsd /etc/default/gpsd

#dpkg should start gpsd in background, so don't run gpsd:
#gpsd /dev/ttyAMA0 -F /var/run/gpsd.sock

cgps -s


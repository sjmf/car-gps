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
# cgps -s

# Copy files into /opt/
mkdir /opt/stomp-gps || exit 1
cp -r * /opt/stomp-gps/
chmod +x /opt/stomp-gps/stomp-gps.py

# Open an editor to set correct config vars
if [ ! $EDITOR ]; then 
    EDITOR=nano
fi

echo "Opening $EDITOR to set STOMP config. Press return to continue"
read
$EDITOR /opt/stomp-gps/config/stomp-config.json
echo to edit this file again run: \`$EDITOR /opt/car-gps/stomp-config.json\`


# Add gps script to start on boot
echo "Setting up boot scripts in /etc/rc.local"
if [[ "$(tail -n1 /etc/rc.local)" == "exit 0" ]]; 
then 
	echo "Removing exit 0 from end of /etc/rc.local"
	head -n -1 /etc/rc.local > rc.local.tmp
	mv rc.local.tmp /etc/rc.local
fi


echo "# Run stomp-gps script"  >> /etc/rc.local
echo "echo \"Run stomp-gps script\""  >> /etc/rc.local
echo "/opt/stomp-gps/run-gps.sh >/dev/null 2>&1 &" >> /etc/rc.local
echo "" >> /etc/rc.local
chmod +x /etc/rc.local

echo "Done."


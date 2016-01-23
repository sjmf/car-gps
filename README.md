# car-gps
Car GPS tracker using Adafruit Ultimate GPS module, and a RPi Zero

This script streams latitude, longditude, altitude, track, speed and climb from GPS TPV packets to a STOMP message queue.

Uses a 3g dongle to provide network connectvitity. (see (this repo)[https://github.com/sjmf/zte-3g-mf110] for how that's set up).

Some rate-limiting functionality is included to prevent totally draining credit from the account. Use the `--rate` switch to the python script. Further testing is needed to figure out what a good value for this would be. The gps itself receives a TPV every second which is probably superfluous.

#!/bin/bash
cd "$(dirname "$0")"

RETRY=20
while sleep $RETRY;
do
    python stomp-gps.py -c config/stomp-config.json
	echo "Retrying in $RETRY seconds..."
done


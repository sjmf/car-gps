#!/usr/bin/env python
# GPS Receiver to STOMP bridge

import gps, gps.client, json, stomp, ssl

# Parse arguments from command line
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="Transmit all strings, not just lat/lon/etc", action="store_true")
parser.add_argument("-d", "--debug",   help="Print GPS NMEA output to terminal", action="store_true")
parser.add_argument("-c", "--config",  help="Configuration file for STOMP")
args = parser.parse_args()


# When running with terminal output on
import pprint
pp = pprint.PrettyPrinter(indent=4).pprint


# Unwrap (recursively) gps.client.dictwrapper objects
def unwrap(dw):
    if not isinstance(dw, gps.client.dictwrapper):
        return dw
    
    d = dw.__dict__
    for k,v in d.iteritems():
        if isinstance(d, gps.client.dictwrapper):
            d[k] = unwrap(v)
        elif type(v) is list:
            d[k] = [ unwrap(w) for w in v ]
    return d



# Get STOMP credentials from the environment
def auth_stomp():
    stomp_conf = None

    if not args.config:
        raise Exception("No configuration file provided")

    with open(args.config, 'r') as f:
        stomp_conf = json.load(f)

    if stomp_conf["host"] is None or stomp_conf["port"] is None or stomp_conf["publish"] is None or stomp_conf["user"] is None or stomp_conf["pass"] is None:
        raise Exception("STOMP Auth Exception")

    return stomp_conf


# Set up the STOMP connection
def setup_stomp():
    global conn, stomp_conf
    if args.debug:
        print("Setting up new STOMP connection")

    stomp_conf = auth_stomp()

    conn = stomp.Connection(
        host_and_ports=[(stomp_conf['host'],stomp_conf['port'])],
        heartbeats=(stomp_conf['heartbeat_in'],stomp_conf['heartbeat_out']),
        reconnect_attempts_max=100)
    
    if stomp_conf['ssl']:
        conn.set_ssl(
            for_hosts=[(stomp_conf['host'],stomp_conf['port'])],
            ssl_version=ssl.PROTOCOL_TLSv1_2)

    conn.start()
    conn.connect(stomp_conf['user'], stomp_conf['pass'], wait=True)


# Send a message
def stomp_send(msg):
    for q in stomp_conf['publish']:
        conn.send(q, msg)


# Main
def main():
    # Listen on port 2947 (gpsd) of localhost
    session = gps.gps("localhost", "2947")
    session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
    
    while True:
        try:
            report = unwrap( session.next() )
            
            if args.debug:
                pp(report)
                print("\n")
            
            if args.verbose:
                # Send whole report
                stomp_send(json.dumps(report))
            else:
                # Filter 'TPV' reports for interesting values
                if report['class'] == 'TPV':
                    to_send = {}
                    
                    #time   Time/date stamp in ISO8601 format, UTC.
                    if hasattr(report, 'time'):
                       to_send['time'] = report.time
                    #lat     Latitude in degrees: +/- signifies North/South
                    if hasattr(report, 'lat'):
                       to_send['lat'] = report.lat
                    #lon     Longitude in degrees: +/- signifies East/West
                    if hasattr(report, 'lon'):
                       to_send['lon'] = report.lon
                    #alt     Altitude in meters
                    if hasattr(report, 'alt'):
                       to_send['alt'] = report.alt
                    #track   Course over ground, degrees from true north.
                    if hasattr(report, 'track'):
                       to_send['track'] = report.track
                    #speed   Speed over ground, meters per second.
                    if hasattr(report, 'speed'):
                       to_send['speed'] = report.speed
                    #climb   Climb (positive) or sink (negative) rate, meters per second.
                    if hasattr(report, 'climb'):
                       to_send['climb'] = report.climb

                    stomp_send(json.dumps(to_send))

                    if args.debug:
                        print("Sent Filtered TPV")

        except KeyError:
            pass
        except KeyboardInterrupt:
            exit()
        except StopIteration:
            session = None
            print("GPSD terminated")

            
if __name__ == '__main__':
    setup_stomp()
    main()

#!/usr/bin/env python
# GPS Receiver to STOMP bridge
import gps, gps.client, json, stomp, ssl, time

# Parse arguments from command line
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-f", "--full",   help="Transmit all GPS output, not just lat/lon/etc", action="store_true")
parser.add_argument("-d", "--debug",  help="Print GPS NMEA output to terminal", action="store_true")
parser.add_argument("-c", "--config", help="Configuration file for STOMP")
parser.add_argument("-r", "--rate",   help="TPV packet forwarding rate limit", action="store_true")
args = parser.parse_args()


# When running with terminal output on
if args.debug:
    import pprint
    pp = pprint.PrettyPrinter(indent=4).pprint


# Print if debugging
def debug_print(*a, **kw):
    if args.debug:
        pp(*a, **kw)


last = 0
def rate_limited(rate = 5):
    global last
    t = time.time()
    if t > last+rate:
        last = t
        return False
    return True



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
    stomp_conf = auth_stomp()
    print("Queue: " + stomp_conf['user'] +'@'+ stomp_conf['host'] +':'+ str(stomp_conf['port']))

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

    if args.debug:
        print("STOMP connected")



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
            
            if args.full:
                # Send whole report
                debug_print(report)
                stomp_send(json.dumps(report))

            elif not rate_limited():
                # Filter 'TPV' reports for interesting values
                if report['class'] == 'TPV':
                    to_send = { a:report[a] for a in [u'time',u'lat',u'lon',u'alt',u'track',u'speed',u'climb'] }

                    debug_print(to_send)
                    stomp_send(json.dumps(to_send))


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


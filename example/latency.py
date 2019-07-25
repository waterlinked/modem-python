"""
Example of sending data  where we are interested in the latest possible value to be transmitted.
Ie. we want to minimize the latency between when the value is read and when it is transmitted by the modem.
This is typically useful when transmitting sensor data.

The example has been tested with the Water Linked Modem-M64.

We don't know exactly when the modem transmits, so we queue data faster than the modem transmits
while flushing the transmit buffer. This ensures that the latest sensor data is available
to the modem when it is ready to transmit.

"""
from __future__ import division, print_function
import logging
import sys
import time
import struct
import argparse
from wlmodem import WlModem


def send(modem):
    """
    Send data while flushing the already queued data to ensure the
    latest available value is sent
    """

    print("Starting sending packets")
    counter = 0

    t0 = time.time()
    while True:
        elapsed = time.time() - t0
        print("Updating latest value to {} after {:.1f}".format(counter, elapsed))
        encoded = struct.pack("<Lf", counter, time.time() - t0)

        # Update queue with latest values
        modem.cmd_flush_queue()
        modem.cmd_queue_packet(encoded)

        # Wait for a bit before updating the latest values in the modem
        time.sleep(0.05)
        counter += 1

def receive(modem):
    """ Receive data """
    print("Starting waiting for packets")
    while True:
        pkt = modem.get_data_packet(timeout=1.0)
        if pkt:
            data = struct.unpack("<Lf", pkt)
            counter, elapsed = data
            print("Got {} with time {:.1f}".format(counter, elapsed))


def main():
    """ Demo code """
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Water Linked Modem example")
    parser.add_argument('-D', '--device', action="store", required=True, type=str, help="Serial port.")
    parser.add_argument('-r', '--role', action="store", type=str, default="a", help="Role: a or b.")
    parser.add_argument('-c', '--channel', action="store", type=int, default=4, help="Channel: 1-7.")
    args = parser.parse_args()

    ch = args.channel
    if ch < 1 or ch > 7:
        print("Error: invalid channel: {}".format(ch))
        sys.exit(1)

    role = args.role
    if role not in ["a", "b"]:
        print("Error: invalid role: {}".format(role))
        sys.exit(1)

    modem = WlModem(args.device)
    if not modem.connect():
        print("Error connecting to modem")
        sys.exit(1)

    print("Set modem role ({}) and channel ({}): ".format(role, ch), end="")
    success = modem.cmd_configure(role, ch)
    if success:
        print("success")
    else:
        print("failed")
        sys.exit(1)

    modem.cmd_flush_queue()

    if args.role == "a":
        send(modem)
    else:
        receive(modem)


if __name__ == "__main__":
    main()

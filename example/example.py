"""
Example of using the wlmodem libarary
"""
from __future__ import division, print_function
import logging
import sys
import time
from wlmodem import WlModem


def main():
    """ Demo code """
    logging.basicConfig(level=logging.DEBUG)
    import argparse
    parser = argparse.ArgumentParser(description="Water Linked Modem example")
    parser.add_argument('-D', '--device', action="store", required=True, type=str, help="Serial port.")
    parser.add_argument('-r', '--role', action="store", type=str, default="a", help="Role: a or b.")
    parser.add_argument('-c', '--channel', action="store", type=int, default=4, help="Channel: 1-7.")
    parser.add_argument('--baudrate', action="store", type=int, default=115200, help="Serial baudrate.")
    parser.add_argument('-v' , '--verbose', action="store_true", help="Verbose.")
    args = parser.parse_args()

    ch = args.channel
    if ch < 1 or ch > 7:
        print("Error: invalid channel: {}".format(ch))
        sys.exit(1)

    role = args.role
    if role not in ["a", "b"]:
        print("Error: invalid role: {}".format(role))
        sys.exit(1)

    modem = WlModem(args.device, debug=args.verbose)
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

    success = modem.cmd_flush_queue()
    print("Flush      :", "success" if success else "failed")

    data = b"HelloSea"
    print("Sending '{}': ".format(data), end="")
    success = modem.cmd_queue_packet(data)
    print("success" if success else "failed")

    import struct
    data = struct.pack(">bbbbbbbb", 8, 7, 6, 5, 4, 3, 2, 1)
    print("Sending encoded numbers {}: ".format(data), end="")
    success = modem.cmd_queue_packet(data)
    print("success" if success else "failed")

    print("Queue length: ", modem.cmd_get_queue_length())
    print("Diagnostic  : ", modem.cmd_get_diagnostic())

    timeout = 10
    while timeout > 0:
        link_up = modem.cmd_get_diagnostic().get("link_up")
        print("Link is " + ("UP" if link_up else "down"))
        if link_up:
            break
        time.sleep(1.0)
        timeout -= 1

    if timeout < 1:
        print("Link cannot be established. Did you start the other modem?")
        return

    print("Wait for packet from other modem. Ctrl-C to abort")
    t0 = time.time()
    try:
        while True:
            pkt = modem.get_data_packet()
            if pkt:
                print("Got:", pkt)
            if t0 + 5 > time.time():
                # Queue another packet after some time
                modem.cmd_queue_packet(data)
                t0 = time.time()

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Stopping")

    print("Diagnostic  : ", modem.cmd_get_diagnostic())


if __name__ == "__main__":
    main()

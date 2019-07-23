# encoding=utf-8
"""
Example of using WlUDPSocket to accept UDP packets and transmit them with a Water Linked Modem.
"""
from __future__ import division, print_function
import logging
import sys
import time
import socket
import argparse
from wlmodem import WlModem, WlUDPSocket


def host_port_from_str(addr):
    parts = addr.split(":")
    host = parts[0]
    port = int(parts[1])
    return host, port


def main():
    """ Demo code """
    parser = argparse.ArgumentParser(description="Water Linked Modem example")
    parser.add_argument('-D', '--device', action="store", required=True, type=str, help="Serial port.")
    parser.add_argument('-r', '--role', action="store", type=str, default="a", help="Role: a or b.")
    parser.add_argument('-c', '--channel', action="store", type=int, default=4, help="Channel: 1-7.")
    parser.add_argument('--baudrate', action="store", type=int, default=115200, help="Serial baudrate.")
    parser.add_argument('-v' , '--verbose', action="store_true", help="Verbose.")
    parser.add_argument('-l' , '--listen', type=str, default="0.0.0.0:7777", help="UDP host and port to listen to")
    parser.add_argument('-s' , '--send', type=str, default="0.0.0.0:7778", help="UDP host and port to send to")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARN)

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

    max_udp_size = 1024  # At 5% packet drop it is very unlikely that larger packets will transfer successfully
    listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, max_udp_size)
    listen.settimeout(0.01)
    _lh, _lp = host_port_from_str(args.listen)

    try:
        listen.bind((_lh, _lp))
        print("Listening to {}:{}".format(_lh, _lp))
    except socket.error as err:
        print("Could not bind to {}: {}".format(args.listen, err))
        return

    send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_host, send_port = host_port_from_str(args.send)
    print("Sending to {}:{}".format(send_host, send_port))

    wl_sock = WlUDPSocket(modem, tx_max=5, debug=args.verbose)

    print("Ready. Waiting for datagram. Ctrl-C to abort")
    try:
        while True:
            try:
                data, addr = listen.recvfrom(max_udp_size)
                print("Got UDP datagram from {}: {} bytes".format(addr, len(data)))
                success = wl_sock.send(data)
                if not success:
                    print("Drop UDP datagram: Too many packets queued")
            except socket.timeout:
                pass


            received = wl_sock.receive()
            if received:
                print("Got msg from modem {} bytes, sending UDP packet to {}".format(len(received), args.send))
                try:
                    send.sendto(received, (send_host, send_port))
                except socket.error as err:
                    print("ERROR: Unable to send UDP packet: {}".format(err))
    except KeyboardInterrupt:
        print("Aborting")

    print("Finished")


if __name__ == "__main__":
    main()
"""
Wireless BlueROV2 control.

This is the receiver which decodes the message from the Water Linked modem and
sends MavLink messages to control a BlueROV2.

"""
from __future__ import print_function, division
import time
import struct
import sys
from wlmodem import WlModem
from pixhawk import Pixhawk


def byte_to_button(val):
    """ Convert button byte to list of values """
    btn = []
    for x in range(8):
        valid = (val >> x) & 0x01
        if valid > 0:
            btn.append(True)
        else:
            btn.append(False)

    return btn


def byte_to_pwm(bytevalue):
    """
    Convert bytevalue 0-255 to PWM

    Return PWM in range 1100-1900
    """
    centered = bytevalue - 127.0  # Range: -127 - 127
    gained = centered * 0.25
    scaled = gained / 127 * 400 # Range: -400 - 400
    return int(scaled) + 1500 #  Range: 1100 - 1900


def run(modem, pix):
    print("Waiting for modem packets")
    timeout_max = 5
    timeout_cnt = 0
    while True:
        pkt = modem.get_data_packet(timeout=1.0)
        if pkt:
            timeout_cnt = timeout_max
            #print("Got data: {}".format(pkt))
            joystick = struct.unpack("BBBBxxBB", pkt)
            print("Got joystick data {}".format(joystick))
            leftX, leftY, rightX, rightY, b_pads1, b_pads2 = joystick
            #print(leftX, leftY, rightX, rightY)
            pads1 = byte_to_button(b_pads1)
            pads2 = byte_to_button(b_pads2)
            #print(pads1, pads2)

            # dup, dright, ddown, dleft, a, b, x, y = pads1
            _, _, _, _, _, b, x, y = pads1
            if b:
                pix.change_mode("MANUAL")
            if x:
                pix.change_mode("ALT_HOLD")
            if y:
                pix.change_mode("STABILIZE")

            pix.set_rc_channel_pwm(4, byte_to_pwm(leftX))
            pix.set_rc_channel_pwm(3, byte_to_pwm(leftY))
            pix.set_rc_channel_pwm(6, byte_to_pwm(rightX))
            pix.set_rc_channel_pwm(5, byte_to_pwm(rightY))

            arm = pads2[0]
            disarm = pads2[1]
            if arm:
                print("Arming!")
                pix.arm()
            if disarm:
                print("Disarming!")
                pix.disarm()
        else:
            # Got no packet, lets stop movement
            pix.set_rc_channel_pwm(4, byte_to_pwm(127))
            pix.set_rc_channel_pwm(3, byte_to_pwm(127))
            pix.set_rc_channel_pwm(6, byte_to_pwm(127))
            pix.set_rc_channel_pwm(5, byte_to_pwm(127))

            timeout_cnt -= 1
            if timeout_cnt < 0:
                # Got no packet for a while, disarming
                print("Timeout, disarming")
                pix.disarm()
                timeout_cnt = timeout_max

        #time.sleep(0.1)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Water Linked Modem example")
    parser.add_argument('-D', '--device', action="store", required=True, type=str, help="Serial port.")
    parser.add_argument('-r', '--role', action="store", type=str, default="b", help="Role: a or b.")
    parser.add_argument('-c', '--channel', action="store", type=int, default=4, help="Channel: 1-7.")
    parser.add_argument('-m', '--mavlink', action="store", type=str, default="udpout:0.0.0.0:9000", help="Mavlink connection to use")
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

    pix = Pixhawk(args.mavlink)
    run(modem, pix)

if __name__ == "__main__":
    main()

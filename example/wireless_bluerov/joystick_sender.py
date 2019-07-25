"""
Wireless BlueROV2 control.

This script reads the XBox controller and updates the modem queue to always have the latest
joystick positions, so that when it is sent we are sure it is always the latest values.

To read the joystick we use:
https://github.com/FRC4564/Xbox

Download the xbox controller script with:
wget https://raw.githubusercontent.com/FRC4564/Xbox/master/xbox.py

"""
import time
import struct
import sys
import xbox
from wlmodem import WlModem


def button_to_byte(tpl):
    """ Convert button tuple to byte """
    return sum([v<<k for k,v in enumerate(tpl)])


def clamp(val, min, max):
    """ Clamp value between min/max values """
    if val > max:
        return max
    if val < min:
        return min
    return val


def stick_to_byte(val):
    """" Convert float -1 to 1 to byte (0-255) """
    adjusted = int((val+1.0)/2.0 * 255)
    return clamp(adjusted, 0, 255)


def run(joy, modem):
    print("Starting to send joystick data")
    while True:
        sticks = (joy.leftX(), joy.leftY(), joy.rightX(), joy.rightY())

        stickbytes = [stick_to_byte(x) for x in sticks]

        pads1 = (joy.dpadUp(), joy.dpadRight(), joy.dpadDown(), joy.dpadLeft(), joy.A(), joy.B(), joy.X(), joy.Y())
        pads2 = (joy.Start(), joy.Back())

        pads1byte = button_to_byte(pads1)
        pads2byte = button_to_byte(pads2)

        all_bytes = stickbytes
        all_bytes.extend([pads1byte, pads2byte])
        print("Sending values: {}".format(all_bytes))
        encoded = struct.pack("BBBBxxBB", *all_bytes)

        # Update queue with latest joystick values
        modem.cmd_flush_queue()
        modem.cmd_queue_packet(encoded)

        time.sleep(0.05)


def main():
    import argparse
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

    joy  = xbox.Joystick()

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

    success = modem.cmd_flush_queue()

    print("Modem connected")

    try:
        run(joy, modem)
    except KeyboardInterrupt:
        pass
    finally:
        joy.close()

if __name__ == "__main__":
    main()

# Water Linked Modem-M64 Wireless BlueROV2

## Notice

This is a prototype which is not maintained, so code quality is not as good as we normally produce and it might not work any more.

## About

This is a one-off prototype of how to do wireless control of a BlueROV2 using the Water Linked Modem-M64.

The code replicate the tech-demo we did in this video:

[![Water Linked Wireless BlueROV2](https://img.youtube.com/vi/rLKCcMMC1Y0/0.jpg)](https://www.youtube.com/watch?v=rLKCcMMC1Y0)

In the video we used a protoype modem with lower latency which made it more useful. Controlling the BlueROV2 with the Modem-M64 is not practical due to the introduced latency, but it works! Sending waypoints for the BlueROV2 to navigate to would be a much better use of the Modem-M64.

With that out of the way: Try it and have fun playing around wirelessly!

## Requirements

* 2x Water Linked Modem-M64
* Xbox 360 controller
* BlueROV2


## Installing

The steps below are the approximately what we did, we might have missed some steps or typed them wrong.

### Topside

On the controlling computer side installed xboxdrv and then connected the Xbox controller:

```
sudo apt-get install xboxdrv
# Verify that it works
sudo xboxdrv --detach-kernel-driver

wget https://raw.githubusercontent.com/FRC4564/Xbox/master/xbox.py

```

Then we set up the python environment

```
python3 -m virtualenv venv
source venv/bin/activate
python3 -m pip install wlmodem

```

We then connected the Modem-M64 via an USB-Serial adapter, and started the script with:

```
sudo venv/bin/python joystick_sender.py -D /dev/ttyUSB1
```

### On BlueROV2

On the ROV we connected the Modem-M64 via an USB-Serial adapter and used the `joystick_receiver.py` script to send the received
joystick data via MavLink messages:

```
python joystick_receiver.py -D /dev/ttyUSB0
```

There is a gain factor on the axis to make it easier to control and we have set up the axis to replicate a Mode-2 radio transmitter. Adjust according to your preferences.

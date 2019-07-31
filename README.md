# Python library for Water Linked underwater modems

[![PyPI version](https://badge.fury.io/py/wlmodem.svg)](https://badge.fury.io/py/wlmodem)
[![Build Status](https://travis-ci.org/waterlinked/modem-python.svg?branch=master)](https://travis-ci.org/waterlinked/modem-python)

Python library for communicating with Water Linked underwater modems.

The library exposes the functionality of the modem: setting configuration, getting diagnostic, sending
and receiving packets.

## Resources

* [Water Linked web site](https://waterlinked.com/underwater-communication/)
* [Modem documentation](https://waterlinked.github.io/docs/modems/modem-m64/)
* [Modem protocol specification](https://waterlinked.github.io/docs/modems/modem-m64-protocol/)
* [Repository](https://github.com/waterlinked/modem-python)

## Requirements

* Python 2.7 or Python 3.6
* pyserial
* crcmod

## Supported modems

* Water Linked Modem-M64

## Setup

```
$ python3 -m pip install --user wlmodem
or
(venv)$ python3 -m pip install wlmodem
```

## Quick start

Connecting to a modem and configuring the mode and channel:

```py
$ python3

>>>  from wlmodem import WlModem
>>>  modem = WlModem("/dev/ttyUSB0")
>>>  modem.connect()
True
>>>  modem.cmd_configure("a", 4)
True
>>>  modem.cmd_queue_packet(b"HelloSea")
True
```

## Usage

The `WlModem` class provides an easy interface to configure, send and receive data with a Water Linked modem.
A pair of modems must be configured on the same channel and with different roles to establish communication between them.

A `WlModem` object is initialized with the serial device name:

```py
from wlmodem import WlModem
modem = WlModem("/dev/ttyUSB0")
```

Call `connect()` to establish communication with the device

```py
if not modem.connect():
    print("Failed connecting to modem")
    sys.exit(1)
```

Once connected we set the same channel and different roles on the pair of modems:

```py
# On modem 1:
success = modem.cmd_configure("a", 4)
# On modem 2:
success = modem.cmd_configure("b", 4)
```

If the tip of the modems are close to each other (<5cm) the modems will now link up.
The link status can be seen on the LEDs or by getting the diagnostic data.

```py
if modem.cmd_get_diagnostic().get("link_up"):
    print("Link is up")
```

Once we have connected we can use `cmd_queue_packet` function to queue data for transmission.

```py
success = modem.cmd_queue_packet(b"HelloSea")
```

In order to get data which one modem has received from the other modem use the `get_data_packet` function.
This function will by default wait `timeout` seconds until a data packet is received before returning.
If `timeout` is 0 it will immediately return with a packet (if available) or `None` if no packet has been received.

```py
pkt = modem.get_data_packet(timeout=0)
if pkt:
    print("Got data:", pkt)
```

## UDP-style transfers

The `WlUDPSocket` class is a higher level abstraction which allows arbitrary sized UDP-like datagrams to be transferred.
This style of transfer is suitable for short messages and has low overhead at 3 bytes for each
datagram (1 start byte, 1 checksum and 1 end byte).
The datagram will be corrupted by any single modem packet dropped (while still taking the full time to transmit),
which means it is only suitable for short datagrams.
The Modem-M64 has a payload size of 8 bytes, so the chance of success given a chance of any packet lost and number of packets transferred is given by:

chance of success = (100 - chance of packet loss) / 100 ^ (number of packets sent) * 100

For example, with a 5% chance of packet loss and datagram of 77 bytes (with the 3 overhead bytes this gives 10 packets):

chance of success = (1.0-0.05)**10 * 100 = 59.8%

```py
from wlmodem import WlModem, WlUDPSocket
modem = WlModem("/dev/ttyUSB0")
modem.connect()
wl_sock = WlUDPSocket(modem)
wl_sock.send(b"There is an art, it says, or rather, a knack to flying. The knack lies in learning how to throw yourself at the ground and miss")
received = wl_sock.receive()
```

## Simulator

A `WlModemSimulator` class can be used to simulate communication with a modem without a physical modem.
Once instantiated the object will behave similarly to a Water Linked Modem-M64.
Data packets that are queued using the simulator object is returned after a timeout.

```py
>>> from wlmodem import WlModemSimulator
>>> modem = WlModemSimulator()
>>> modem.connect()
True
>>> modem.cmd_queue_packet(b"HelloSim")
True
>>> modem.get_data_packet()
b'HelloSim'
```

## Examples

Multiple examples showing how to use the API is available in the [example/](example/) folder.

## Development

The code in this repository is unit tested with `pytest`. `tox` is used to automate testing on multiple Python versions.

Run unit-tests with:

```
pip install tox
tox
```

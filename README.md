# wlmodem

Python library for communicating with Water Linked underwater modems.

The library exposes the functionality of the modem: setting configuration, getting diagnostic, sending
and receiving packets.

## Resources

* [Water Linked web site](https://waterlinked.com/underwater-communication/)
* [Modem documentation](https://waterlinked.github.io/docs/modems/modem-m64/)
* [Modem protocol specification](https://waterlinked.github.io/docs/modems/modem-m64-protocol/)

## Requirements

* Python 2.7 or Python 3.6
* pyserial
* crcmod

## Setup

```
$ python -m pip install --user crcmod pyserial wlmodem
or
(venv)$ python -m pip install crcmod pyserial wlmodem
```

## Usage

Connecting to a modem and configuring the mode and channel:

```python
$ python

>>>  from wlmodem import WlModem
>>>  modem = WlModem("/dev/ttyUSB0")
>>>  modem.connect()
>>>  modem.cmd_configure("a", 4)
True
>>>  modem.cmd_queue_packet(b"HelloSea")
True
```

A larger example is available in [example/example.py](example/example.py).

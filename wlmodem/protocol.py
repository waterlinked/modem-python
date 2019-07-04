# encoding=utf-8
"""
Water Linked Modem protocol parser
"""
from __future__ import print_function, division
import logging
import time
import sys
import serial
HAS_CRC = False
try:
    import crcmod
    HAS_CRC = True
except ImportError:
    # Install crcmod to support CRC checking:
    # pip install crcmod
    pass


# Logger
log = logging.getLogger(__file__)

# Python2 detection
IS_PY2 = False
if sys.version_info < (3, 0):
    IS_PY2 = True


# Protocol definitions
SOP = ord('w')
EOP = ord('\n')
DIR_CMD = ord('c')
DIR_RESP = ord('r')
CHECKSUM = ord('*')

CMD_GET_VERSION = ord('v')
CMD_GET_PAYLOAD_SIZE = ord('n')
CMD_GET_BUFFER_LENGTH = ord('l')
CMD_GET_DIAGNOSTIC = ord('d')
CMD_GET_SETTINGS = ord('c')
CMD_SET_SETTINGS = ord('s')
CMD_QUEUE_PACKET = ord('q')
CMD_FLUSH = ord('f')
RESP_GOT_PACKET = ord('p')
ALL_VALID = [
    CMD_GET_VERSION,
    CMD_GET_PAYLOAD_SIZE,
    CMD_GET_BUFFER_LENGTH,
    CMD_GET_DIAGNOSTIC,
    CMD_GET_SETTINGS,
    CMD_SET_SETTINGS,
    CMD_QUEUE_PACKET,
    CMD_FLUSH,
    RESP_GOT_PACKET,
]


def is_eop(ch):
    """ Is the given byte an eop """
    return ch in (b'\n', b'\r')


def is_checksum(ch):
    """ Is the given byte an checksum char """
    #print(type(ch), ch, chr(ch))
    #print("Checksum ", type(CHECKSUM), ord(CHECKSUM), CHECKSUM)
    if isinstance(ch, bytes):
        return ord(ch) == CHECKSUM
    return ch == CHECKSUM


def is_ack(ch):
    """ Is this an acknowledge """
    return ch == b'a'


def get_binary_payload_size(sentence):
    """ Detect if this is the start of a binary payload and return the number of bytes it contains """
    # For example: 'wcq,8,'
    if len(sentence) != 6:
        return -1
    if sentence[0] != SOP:
        return -1
    if sentence[2] not in [CMD_QUEUE_PACKET, RESP_GOT_PACKET]:
        return -1
    fragments = sentence.split(b',', 2)  # Split on comma, but don't touch the binary data
    if len(fragments) < 2:
        return -1
    try:
        _len = int(fragments[1])
        return _len
    except ValueError:
        return -1


class WlModemGenericError(Exception):
    """ Generic error """


class WlProtocolParseError(WlModemGenericError):
    """ Error parsing sentence """


class WlProtocolChecksumError(WlProtocolParseError):
    """ Sentence checksum is invalid """


class ModemSentence(object):
    """ ModemSentence represents a message to/from the modem """
    def __init__(self, cmd, direction, options=None):
        self.cmd = cmd
        self.dir = direction
        self.options = options

    def __repr__(self):
        _dir = "CMD" if self.dir == DIR_CMD else "RESP"
        return "ModemSentence[c={} dir={} options={}]".format(chr(self.cmd), _dir, self.options)


class WlProtocolParser(object):
    """
    Water Linked Modem protocol parser
    """
    def __init__(self):
        self.crc_func = None
        if HAS_CRC:
            self.crc_func = crcmod.predefined.mkPredefinedCrcFun("crc-8")

    @staticmethod
    def do_format_checksum(checksum):
        if IS_PY2:
            return bytes("*{:02x}".format(checksum))

        return bytes("*{:02x}".format(checksum), "ascii")

    def checksum_for_buffer(self, data):
        if not self.crc_func:
            raise WlModemGenericError("pip install crcmod to get support for checksum")
        if IS_PY2:
            csum = self.crc_func(bytes(data))
        else:
            csum = self.crc_func(data)
        return self.do_format_checksum(csum)

    def do_frame_fragments(self, cmd, direction, options, checksum):
        """ Frame response. Direction (c/r). Options are optional. """
        resp = bytearray([SOP, direction, cmd])

        if options:
            resp.append(ord(","))
            resp.extend(b",".join(options))

        csum = b""
        if checksum:
            csum = self.checksum_for_buffer(resp)
        return resp, csum

    def do_frame(self, cmd, direction=DIR_CMD, options=None, checksum=False):
        if isinstance(cmd, bytes):
            cmd = cmd[0]
        resp, csum = self.do_frame_fragments(cmd, direction, options, checksum)
        resp.extend(csum)
        resp.append(EOP)
        return resp

    def parse(self, sentence):
        sop = sentence[0]
        if isinstance(sop, bytes):
            sop = ord(sop)
        if sop != SOP:
            # This will swallow LF following a CR and garbage
            raise WlProtocolParseError("Missing SOP: Got {} Expected {}".format(sop, SOP))
        if len(sentence) < 3:  # Shortest possible command is 3, SOP+DIR+CMD
            raise WlProtocolParseError("Sentence is too short")

        direction = sentence[1]
        if isinstance(direction, bytes):
            direction = ord(direction)
        if direction not in [DIR_CMD, DIR_RESP]:
            raise WlProtocolParseError("Invalid direction {}: {}".format(direction, sentence))

        got_checksum = is_checksum(sentence[-3])
        csum = ""
        if got_checksum:
            csum = sentence[-3:]
            sentence = sentence[:-3]  # Remove checksum to ease further processing
            if csum != self.checksum_for_buffer(sentence):
                expect = self.checksum_for_buffer(sentence)
                raise WlProtocolChecksumError("Expected {} got {}".format(expect, csum))

        cmd = sentence[2]
        if isinstance(cmd, bytes):
            cmd = ord(cmd)
        if cmd in ALL_VALID:
            if cmd in [CMD_QUEUE_PACKET, RESP_GOT_PACKET]:
                # Payload is binary, so only split until payload
                fragments = sentence.split(b',', 2)
            else:
                fragments = sentence.split(b',')
            options = None
            if len(fragments) > 1:
                options = fragments[1:]

            return ModemSentence(cmd, direction, options)

        return None


class WlModemBase(object):
    """
    Water Linked Modem protocol parser base class
    """

    def __init__(self, iodev, debug=False):
        self._iodev = iodev
        self.parser = WlProtocolParser()

        self.payload_size = -1

        self._holdoff = 0
        self._buffer = bytearray()
        self.debug = debug

        self._rx_queue = list()

    # --------------------
    # Public API functions
    # --------------------
    def connect(self):
        """ Connect to modem and get version and supported payload size """
        # Verify the modem responsd and is a supported version
        log.info("Connect to Water Linked Modem on %s", self._iodev.port)
        self.send_reset()
        version = self.cmd_get_version()
        if not version:
            log.error("Timeout connecting to modem")
            return False
        if version[0] != 1:
            log.warn("Unsupported major version {}".format(version))
            return False

        version = ".".join([str(x) for x in version])
        log.info("Connect success. Modem protocol version %s", version)

        # Get payload size
        payload = self.cmd_get_payload_size()
        if not payload:
            log.warn("Timeout getting payload size")
            return False
        self.payload_size = payload

        log.info("Connect success. Modem payload size %d", self.payload_size)
        return True

    def cmd_get_version(self, timeout=0.5):
        """ Get modem version """
        pkt = self.request(CMD_GET_VERSION, timeout=timeout)
        if not pkt:
            return None

        version = [int(x) for x in pkt.options]
        return version

    def cmd_get_payload_size(self, timeout=0.5):
        """ Payload size """
        pkt = self.request(CMD_GET_PAYLOAD_SIZE)
        if not pkt:
            return 0

        return int(pkt.options[0])

    def cmd_queue_packet(self, data):
        """ Queue a data packet for transmission. Data must be of type bytes or bytearray """
        if self.payload_size < 1:
            raise WlModemGenericError("Connect before queueing data")
        # Anyone has a way of checking for bytes which supports duck-typing?
        # The suggestion from https://stackoverflow.com/a/34870210 doesn't seem to work in Python 3
        if not isinstance(data, (bytes, bytearray)):
            raise WlModemGenericError("Please encode data as bytes")
        if len(data) != self.payload_size:
            raise WlModemGenericError("Invalid payload size {} expected {}".format(len(data), self.payload_size))
        if IS_PY2:
            _size = bytes("{}".format(self.payload_size))
        else:
            _size = bytes("{}".format(self.payload_size), "ascii")
        pkt = self.request(CMD_QUEUE_PACKET, options=[_size, data])
        if pkt:
            return is_ack(pkt.options[0])
        return False

    def get_data_packet(self, timeout=5):
        """
        Get data packet from another modem.

        Timeout specifies how long to wait until a data packet is available.
        If no packet is available None is returned
        """
        if self._rx_queue:
            pkt = self._rx_queue.pop(0)
            return pkt.options[1]
        if timeout > 0:
            # Got a timeout
            pkt = self.wait_sentence(RESP_GOT_PACKET, timeout=timeout)
            if pkt:
                return pkt.options[1]
        else:
            # Return imediately
            msg = self.get_packet()
            if msg and msg.cmd == RESP_GOT_PACKET:
                return msg.options[1]
        return None

    def cmd_configure(self, role, channel, timeout=2):
        """ Set modem configurations: role (a,b) and channel (1-7) """
        role = role.encode()
        if channel < 1 or channel > 7:
            raise WlModemGenericError("Invalid channel {}".format(channel))
        channel = "{:d}".format(channel).encode()
        pkt = self.request(CMD_SET_SETTINGS, options=[role, channel], timeout=timeout)
        if pkt:
            # Return success if we get an acknowledge
            return is_ack(pkt.options[0])
        # Timed out while waiting for a response
        return False

    def cmd_get_queue_length(self, timeout=0.5):
        """ Get transmit queue length """
        pkt = self.request(CMD_GET_BUFFER_LENGTH, timeout=timeout)
        if pkt:
            return int(pkt.options[0])
        # Got nothing
        return -1

    def cmd_flush_queue(self, timeout=0.5):
        """ Flush the transmit queue """
        pkt = self.request(CMD_FLUSH, timeout=timeout)
        if pkt:
            return is_ack(pkt.options[0])
        return False

    def cmd_get_diagnostic(self, timeout=0.5):
        """ Get diagnostic data """
        pkt = self.request(CMD_GET_DIAGNOSTIC, timeout=timeout)
        if pkt:
            diag = {
                "link_up": pkt.options[0] == b'y',
                "pkt_cnt": int(pkt.options[1]),
                "pkt_loss_cnt": int(pkt.options[2]),
                "bit_error_rate": float(pkt.options[3])
            }
            return diag
        # Timed out, so returning empty dict
        return dict()

    # ----------------------------------
    # Lower level and internal functions
    # ----------------------------------
    def _dbg(self, *args, **kwargs):
        if self.debug:
            log.debug(*args, **kwargs)
            #print(*args, **kwargs)

    def send_reset(self):
        """ Send newline to ensure we start fresh with the modem """
        if IS_PY2:
            self._write(chr(EOP))  # Reset in case there is something in the buffer
        else:
            self._write(bytes([EOP]))  # Reset in case there is something in the buffer

    def request(self, cmd_id, options=None, timeout=0.5):
        """ Send a request and wait for the response """
        self._write(self.parser.do_frame(cmd_id, options=options))
        return self.wait_sentence(cmd_id, timeout=timeout)

    def wait_sentence(self, resp_id, timeout=5.0, sleep_time=0.001):
        """ Wait for a specific response from modem """
        start = time.time()
        while time.time() - start < timeout:
            msg = self.get_packet()
            if msg:
                if msg.cmd == resp_id:
                    return msg
                if msg.cmd == RESP_GOT_PACKET:
                    self._rx_queue.append(msg)
            if sleep_time:
                time.sleep(sleep_time)
        return None

    def get_packet(self):
        """ Read data the data waiting in the serial buffer.

        If more data is needed return None

        If a full packet has been received decode and return a ModemSentence object.
        If packet decoding fails raise WlProtocolParseError
        If packet checksum is incorret raise WlProtocolChecksumError
        """
        is_done = False
        while self._iodev.in_waiting > 0:
            data = self._iodev.read(1)

            if len(data) < 1:
                # This should not happen since in_waiting is > 0, but let's be safe
                continue

            if len(self._buffer) == 0 and len(data) == 1 and is_eop(data):
                # Swallow newline when buffer is empty to allow both \n and \r\n
                self._dbg("swallow {}".format(data))
                continue

            if self._holdoff > 0:
                self._buffer.append(ord(data))
                self._holdoff -= len(data)
                self._dbg("holdoff {} {}".format(self._holdoff, self._buffer))
            elif is_eop(data):
                # We got an EOP, we swallow it and parse the data
                self._dbg("eop")
                is_done = True
            else:
                self._buffer.append(ord(data))
                self._dbg("add {}".format(self._buffer))

            if self._holdoff == 0:
                _size = get_binary_payload_size(self._buffer)
                if _size > 0:
                    # We have a binary payload, next bytes must be parsed as binary
                    self._holdoff = _size

            if self._holdoff > 0:
                # Need more data before we have a full packet
                continue

            if not is_done:
                # Don't have EOP yet, need more data
                self._dbg("more please")
                continue

            try:
                self._dbg("parse {}".format(self._buffer))
                packet = self.parser.parse(self._buffer)
                # Got packet, return it
                self._reset_buffer()
                self._dbg("parse success {}".format(packet))
                return packet
            except WlProtocolChecksumError as err:
                self._dbg("checksum error {}: {}".format(self._buffer, err))
                self._reset_buffer()
                raise
            except WlProtocolParseError as err:
                # Malformed
                self._dbg("malformed {}: {}".format(self._buffer, err))
                self._reset_buffer()
                raise

        # Haven't gotten a full packet yet
        return None

    def _write(self, data):
        """ Write data to serial port """
        self._dbg("Write {} {}".format(data, type(data)))
        return self._iodev.write(data)

    def _reset_buffer(self):
        """ Reset internal buffer """
        self._dbg("Reset")
        self._holdoff = 0
        self._buffer = bytearray()


class WlModem(WlModemBase):
    """
    Water Linked Modem protocol parser
    """

    def __init__(self, device, baudrate=115200, debug=False):
        try:
            self._serial = serial.Serial(device, baudrate)
        except Exception as err:
            raise WlModemGenericError("Error opening serial port {}".format(err))

        super(WlModem, self).__init__(self._serial, debug=debug)

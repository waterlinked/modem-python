# encoding=utf-8
"""
Water Linked Modem simulator
"""
from __future__ import print_function, division
import time
from .protocol import WlModemBase
from .protocol import CMD_FLUSH, CMD_GET_BUFFER_LENGTH, CMD_GET_DIAGNOSTIC, CMD_GET_VERSION
from .protocol import CMD_GET_PAYLOAD_SIZE, CMD_SET_SETTINGS, CMD_QUEUE_PACKET
from .protocol import DIR_RESP
from .protocol import ModemSentence


class MockIODev():
    """ Mock io device for simualtor and unit testing """
    def __init__(self, in_buf):
        self.in_buf = bytearray(in_buf)
        self.out_buf = bytearray()

    @property
    def in_waiting(self):
        return len(self.in_buf)

    def read(self, n):
        if self.in_buf:
            buf = bytearray()
            buf.append(self.in_buf.pop(0))
            return bytes(buf)

    def write(self, data):
        if isinstance(data, bytearray):
            self.out_buf.extend(data)
        else:
            for ch in data:
                self.out_buf.append(ch)

    def feed(self, data):
        for x in bytes(data):
            self.in_buf.append(x)

    @property
    def port(self):
        return "MockPort"


class WlModemSimulator(WlModemBase):
    """
    Water Linked Modem Mock. This simulates a Modem-M64 and can be used for testing/integration without a physical modem
    """
    def __init__(self, link_up_duration=3.0, queue_duration=1.0, next_duration=1.0):
        dev = MockIODev(b"")
        super(WlModemSimulator, self).__init__(dev)
        self.tx_queue = list()

        self._link_up_duration = link_up_duration  # Time 
        self._packet_queue_duration = queue_duration
        self._next_packet_duration = next_duration

        self.sent = 0
        self._link_up_time = time.time()
        self._next_packet_time = time.time() + self._next_packet_duration

    def _is_link_up(self):
        return self._link_up_time < time.time()

    def request(self, cmd_id, options=None, timeout=0.5):
        """ Send a request and wait for the response """
        time.sleep(0.05) # Use some time to process
        if cmd_id == CMD_GET_VERSION:
            return ModemSentence(cmd_id, DIR_RESP, options=[b'1',b'0',b'1'])
        elif cmd_id == CMD_GET_PAYLOAD_SIZE:
            return ModemSentence(cmd_id, DIR_RESP, options=[b'8'])
        elif cmd_id == CMD_GET_BUFFER_LENGTH:
            _len = len(self.tx_queue)
            _b = "{}".format(_len).encode("ascii")
            return ModemSentence(cmd_id, DIR_RESP, options=[_b])
        elif cmd_id == CMD_FLUSH:
            # self.tx_queue.clear() # Python 3
            self.tx_queue = list()  # Clear list Python 2 and 3
            return ModemSentence(cmd_id, DIR_RESP, options=[b'a'])
        elif cmd_id == CMD_SET_SETTINGS:
            self._link_up_time = time.time() + self._link_up_duration
            return ModemSentence(cmd_id, DIR_RESP, options=[b'a'])
        elif cmd_id == CMD_GET_DIAGNOSTIC:
            link_up = b'y' if self._is_link_up() else b'n'
            return ModemSentence(cmd_id, DIR_RESP, options=[link_up, self.sent, 0, 3.5])
        elif cmd_id == CMD_QUEUE_PACKET:
            self.tx_queue.append(options[1])
            return ModemSentence(cmd_id, DIR_RESP, options=[b'a'])
        return None

    def get_data_packet(self, timeout=5):
        if self.tx_queue and self._is_link_up():
            if time.time() > self._next_packet_time:
                self._next_packet_time = time.time() + self._next_packet_duration
                self.sent += 1
                pkt = self.tx_queue.pop(0)
                return self.transform(pkt)

        time.sleep(timeout)
        return None

    def transform(self, pkt):
        """ Modify packet before returning it """
        return pkt

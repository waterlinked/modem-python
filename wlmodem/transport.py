# encoding=utf-8
"""
Arbitrary size data transfers for Water Linked Underwater Modems

WlUDPSocket is the interface for sending/receiving arbitrary length data (datagram) with
a Water Linked Underwater Modem.

This style of transfer is suitable for short messages and has low overhead at 3 bytes for each
datagram (1 start byte, 1 checksum and 1 end byte).
The datagram will be corrupted by any single modem packet dropped (while still taking the full time to transmit),
which means it is only suitable for short datagrams.
The Modem-M64 has a payload size of 8 bytes and hence messages, so the chance of success with given
chance of any packet lost is given by:

chance of success = (100 - chance of packet loss) / 100 ^ (number of packets sent) * 100

For example, with a 5% chance of packet loss and datagram of 77 bytes (with the 3 overhead bytes this gives 10 packets):

chance of success = (1.0-0.05)**10 * 100 = 59.8%

Internally it uses a thread to frame, packetizes and sends the datagrams given via the "send" function.
When a full datagram is received by the modem it is put on a queue and can be retrieved with the "receive" function.

"""
from __future__ import division, print_function
import threading
try:
    import queue
except ImportError:
    import Queue as queue
import time
import logging
from abc import abstractmethod
from cobs import cobsr as cobs
import crcmod


# Logger
log = logging.getLogger(__file__)

### Debug
def printable(ch):
    if ch < 32:
        return "."
    if ch > 127:
        return "."
    return chr(ch)


def pretty_packet(pkt):
    _hx = " ".join("{:02x}".format(x) for x in pkt)
    return "[{}] {}".format(_hx, "".join([printable(x) for x in pkt]))


FRAME_END = 0  # COBS guarantees no zeros in the payload
# The payload is internally checksummed by the modem, but we need to detect if a packet is dropped
# so a simple CRC-8 is sufficient
crc_func = crcmod.predefined.mkPredefinedCrcFun("crc-8")


def frame(data):
    """ Frame data using COBS for transmission """
    crc = crc_func(data)
    framed = bytearray(data)
    framed.append(crc)
    framed = cobs.encode(framed)
    framed = bytearray(framed)
    framed.append(FRAME_END)
    return framed


def pad_payload(data, payload_size):
    """
    Pad data with zero data until it's size is the same as the given payload_size
    """
    send = bytearray(data)

    left = payload_size - len(send)
    while left >= 2:
        # Pad with an (COBS) empty frame
        send.append(1)  # COBS Start byte
        send.append(FRAME_END)
        left = payload_size - len(send)
    if left == 1:
        # Pad with a frame end
        send.append(FRAME_END)

    return send


def unframe(buffer):
    """ Decode frame and return data """
    # Remove terminating 0
    if buffer and buffer[-1] == 0:
        buffer.pop()

    try:
        decoded = cobs.decode(buffer)
    except cobs.DecodeError as err:
        log.warn("MSG Decode error {}".format(err))
        return False

    if not decoded:
        # Padding/Fill frame only, don't do anything
        return None

    expected_crc = decoded[-1]
    data = decoded[:-1]
    data_crc = crc_func(data)
    if data_crc != expected_crc:
        log.warn("MSG CRC ERR. Expected {} Got {}".format(expected_crc, data_crc))
        return False

    return data


class WlUDPBase():
    """
    WlUDPBase is the base class for sending/receiving arbitrary length data with a Water Linked Underwater Modem
    """
    def __init__(self, modem, desired_queue_length=2, debug=True):
        super().__init__()
        self._tx_buf = bytearray()
        self._rx_buf = bytearray()
        self.modem = modem
        self.desired_queue_length = desired_queue_length
        self.debug = debug

    @property
    def payload_size(self):
        return self.modem.payload_size

    def run_send(self):
        """ Check if we need to add more data to the modem for transmission """
        if self.modem.cmd_get_queue_length() < self.desired_queue_length:
            # Tx queue on modem is getting low, lets add another packet
            if len(self._tx_buf) < self.payload_size:
                # The transmit buffer is less than the payload, let's load more data
                self._fill_tx_buf()

            # Check if we have anything to transmit
            if self._tx_buf:
                # Get the next packet to transmit
                send = self._get_next_tx_packet()
                # Queue the packet
                if self.debug:
                    log.info("Queing packet {}".format(pretty_packet(send)))
                self.modem.cmd_queue_packet(send)

    def run_receive(self):
        """ Check if we have gotten any new data from the modem """
        received = self.modem.get_data_packet(0)
        if received:
            if self.debug:
                log.info("Got packet {}".format(pretty_packet(received)))
            self._rx_buf.extend(received)

            # If we have a \0 we got a datagram
            if self._rx_buf.find(FRAME_END) >= 0:
                if self.debug:
                    log.info("Got full datagram, let's decode it")
                while self._rx_buf.find(FRAME_END) >= 0:
                    frame = self._extract_frame_from_rx_buf()

                    # Remove the framing
                    data = unframe(frame)
                    if data is None:
                        # Fill frame only, ignore that
                        continue

                    if data:
                        self._fill_rx_buf(data)
                    else:
                        # Error occured
                        if self.debug:
                            log.warn("MSG: Invalid")

    @abstractmethod
    def _fill_tx_buf(self):
        """ This function is called when _tx_buf is too short to fill a packet and more data is needed"""
        pass

    def _get_next_tx_packet(self):
        """ Get next packet for modem to transmit """
        send = self._tx_buf[:self.payload_size]
        self._tx_buf = self._tx_buf[self.payload_size:]

        if len(send) < self.payload_size:
            # Too little data available to fill desired payload size, we need to pad it
            send = pad_payload(send, self.payload_size)

        return send

    @abstractmethod
    def _fill_rx_buf(self, data):
        """ This function is called when a full datagram is received to fill the received queue """
        pass

    def _extract_frame_from_rx_buf(self):
        idx = self._rx_buf.find(FRAME_END)

        # Extract the frame
        frame = self._rx_buf[:idx]

        # Remove the frame from tx_buf
        self._rx_buf = self._rx_buf[idx:]
        self._rx_buf.pop(0)  # Remove the FRAME_END
        return frame


class WlUDPSocket(WlUDPBase):
    """
    Arbitrary size data transfers for Water Linked Underwater Modems

    WlUDPSocket is the interface for sending/receiving arbitrary length data (datagram) with
    a Water Linked Underwater Modem.

    See package documentation for more details.

    Internally it uses a thread to frame, packetizes and sends the datagrams given via the "send" function.
    When a full datagram is received by the modem it is put on a queue and can be retrieved with the "receive" function.

    Be careful of accessing the internal variables in this object since it is run in a different thread
    """

    def __init__(self, modem, tx_max=0, rx_max=0, sleep_time=0.2, debug=False):
        """
        Initialize WlUDPSocket. Use "send" to send datagrams and "receive" to get received datagrams.

        tx_max sets the number of datagrams to allow in the send queue
        rx_max sets the number of datagrams to allow in the receive queue
        sleep_time sets the number of seconds before checking if the modem needs more data
        debug can be set to True to enable mode debug output
        """
        WlUDPBase.__init__(self, modem, debug=debug)
        self.sleep_time = sleep_time
        self._tx_queue = queue.Queue(maxsize=tx_max)
        self._rx_queue = queue.Queue(maxsize=rx_max)

        self.run_event = threading.Event()
        self.run_event.set()
        self.worker = threading.Thread(target=self.run, args=())
        self.worker.daemon = True
        # Start thread
        self.worker.start()

    def send(self, data, block=False):
        """
        Add datagram for transmission

        Returns True if successful, False if queue is ful
        """
        try:
            self._tx_queue.put(data, block=block)
            return True
        except queue.Full:
            return False

    def receive(self, block=False):
        """ Get datagram if one is available.
        If block is True it waits until a datagram is available and returns.

        If queue is full, return None
        """
        try:
            return self._rx_queue.get(block=block)
        except queue.Empty:
            return None

    def _fill_tx_buf(self):
        try:
            # Get data
            data = self._tx_queue.get_nowait()
            # Frame it
            framed = frame(data)
            # Add it to the buffer
            self._tx_buf.extend(framed)
        except queue.Empty:
            # No more data available at this time
            pass

    def _fill_rx_buf(self, data):
        # Got some actual data
        try:
            self._rx_queue.put_nowait(data)
            return True
        except queue.Full:
            # Queue full, drop the packet
            return False

    def run(self):
        """ Worker thread main function. You do not need to call this function, it is run automatically """
        while self.run_event.is_set():
            self.run_send()
            self.run_receive()
            time.sleep(self.sleep_time)

    def stop(self):
        """ Stop worker thread """
        self.run_event.clear()
        self.worker.join()

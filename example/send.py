# encoding=utf-8
"""

!!! This is work in progress !!!

This is an example of how to do arbitrary size transfers with a Water Linked modem.

This is a modification of the transfer.py to test using a thread for sending/receiving data packets

"""
from __future__ import division, print_function
import sys
import zlib
import copy
import threading
import queue
import time
from cobs import cobsr as cobs
import crcmod
from wlmodem import WlModem, WlModemSimulator


FRAME_END = 0  # COBS guarantees no zeros in the payload

class WlModemTransfer(threading.Thread):
    """ WlModemTransfer allows data transfer with a Water Linked modem
    
    Be careful of accessing the interal variables, since this is run in a different thread
    """
    def __init__(self, modem):
        super().__init__()
        self.crc_func = crcmod.predefined.mkPredefinedCrcFun("crc-8")
        self._tx_queue = queue.Queue()
        self._tx_buf = bytearray()
        self._rx_queue = queue.Queue()
        self._rx_buf = bytearray()
        self.modem = modem
        self.enable_compression = False
        self.run_event = threading.Event()
        self.run_event.set()

    @property
    def payload_size(self):
        return self.modem.payload_size

    def stop(self):
        self.run_event.clear()

    def run(self):
        while self.run_event.is_set():

            if self.modem.cmd_get_queue_length() < 2:
                # Tx queue on modem is getting low, lets add another packet
                if len(self._tx_buf) < self.payload_size:
                    # The transmit buffer is less than the payload, let's load more data
                    try:
                        # Get data
                        data = self._tx_queue.get_nowait()
                        # Frame it
                        framed = self._frame(data, self.enable_compression)
                        self._tx_buf.extend(framed)
                    except queue.Empty:
                        # No more data available at this time
                        pass

                # Check if we have anything to transmit
                if self._tx_buf:
                    # Get the next packet to transmit
                    send = self._tx_buf[:self.payload_size]
                    self._tx_buf = self._tx_buf[self.payload_size:]

                    if len(send) < self.payload_size:
                        # Too little data available, we need to pad it
                        send = bytearray(send)

                        left = self.payload_size - len(send)
                        while left >= 2:
                            # Pad with an empty frame
                            send.append(1)
                            send.append(0)
                            left = self.payload_size - len(send)
                        if left == 1:
                            send.append(0)

                    # Queue the packet
                    self.modem.cmd_queue_packet(send)

            # Have we gotten any new data?
            received = self.modem.get_data_packet(0.5)
            if received:
                self._rx_buf.extend(received)
                # If we have a \0 we got a full frame
                if received.find(FRAME_END) >= 0:
                    #print("Got full data, let's decode it")
                    while self._rx_buf.find(FRAME_END) >= 0:
                        idx = self._rx_buf.find(FRAME_END)

                        # Extract the frame
                        frame = self._rx_buf[:idx]

                        # Remove the frame from tx_buf
                        self._rx_buf = self._rx_buf[idx:]
                        self._rx_buf.pop(0)  # Remove the FRAME_END

                        # Remove the framing
                        data = self._unframe(frame, self.enable_compression)
                        if data is None:
                            # Fill frame only, ignore that
                            continue

                        if data:
                            # Got some actual data
                            try:
                                self._rx_queue.put_nowait(data)
                            except queue.Full:
                                # Queue full, drop the packet
                                pass
                        else:
                            # Error occured
                            print("Got invalid packet")

    def send(self, data):
        try:
            self._tx_queue.put_nowait(data)
            return True
        except queue.Full:
            return False

    def receive(self):
        try:
            return self._rx_queue.get_nowait()
        except queue.Empty:
            return None

    def _frame(self, data, compression=False):
        """ Frame data for transmission """
        if compression:
            data = zlib.compress(data)

        crc = self.crc_func(data)
        framed = bytearray(data)
        framed.append(crc)
        framed = cobs.encode(framed)
        framed = bytearray(framed)
        framed.append(FRAME_END)
        return framed

    def _unframe(self, buffer, compression=False):
        """ Decode frame and return data """
        # Remove terminating 0
        if buffer and buffer[-1] == 0:
            buffer.pop()

        try:
            decoded = cobs.decode(buffer)
        except cobs.DecodeError as err:
            print("Decode error {}".format(err))
            return False

        if not decoded:
            # Padding/Fill frame only, don't do anything
            return None

        expected_crc = decoded[-1]
        data = decoded[:-1]
        data_crc = self.crc_func(data)
        if data_crc != expected_crc:
            print("CRC failed. Expected {} Got {}".format(expected_crc, data_crc))
            return False

        if compression:
            return zlib.decompress(data)

        return data


def setup(name, role, channel=4, sim=False):
    """ Setup modem or simulated modem if sim is True """
    if sim:
        modem = WlModemSimulator(0, 0.01, 0.01)
    else:
        modem = WlModem(name)
    if not modem.connect():
        print("Error connecting to modem 1")
        sys.exit(1)

    print("Modem[{}] Set modem role {} and channel {}: ".format(name, role, channel), end="")
    success = modem.cmd_configure(role, channel)
    if success:
        print("success")
    else:
        print("failed")
        sys.exit(1)
    return modem


def main():
    """ Main code """
    sim = True
    if sim:
        # Running on simulated modems
        m_tx = setup("sim", "a", sim=True)
        m_rx = m_tx
    else:
        # Running on actual modems
        m_tx = setup("/dev/ttyUSB0", "a")
        m_rx = setup("/dev/ttyUSB1", "b")

    data = "There is an art, it says, or rather, a knack to flying. The knack lies in learning how to throw yourself at the ground and miss."
    data = bytes(data, "utf-8")  # Need it to be binary data

    tx_transfer = WlModemTransfer(m_tx)
    tx_transfer.start()

    try:
        cnt = 24
        wait_time = 2

        add = time.time() + wait_time
        while cnt > 0:
            if time.time() > add:
                to_send = data[:cnt]
                tx_transfer.send(to_send)
                add = time.time() + wait_time
            received = tx_transfer.receive()
            if received:
                cnt -= 1
                print("Got data", received)
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("Stopping")
    finally:
        tx_transfer.stop()
        tx_transfer.join()


if __name__ == "__main__":
    main()

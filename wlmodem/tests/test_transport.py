""" Unittest """
import unittest
import time
from wlmodem import WlModemSimulator
from wlmodem.transport import frame, unframe, pad_payload, pretty_packet, WlUDPSocket


class TestTransport(unittest.TestCase):
    def _make_one(self):
        pass
        #return WlUDPSocket()

    def test_framing(self):
        data = b'helloThere'
        framed = frame(data)
        print([x for x in framed])
        unframed = unframe(framed)
        print(unframed)
        self.assertEqual(data, unframed)

    def test_frame_invalid_crc_is_detected(self):
        data = b'1'
        framed = frame(data)
        print(pretty_packet(framed))
        # Modify the CRC to corrupt the packet
        framed[1] = 3
        self.assertEqual(unframe(data), False)

    def test_padding(self):
        data = b'12345678'

        for x in range(8):
            padded = pad_payload(data[:x], 8)
            self.assertEqual(len(padded), 8, "While padding {}".format(x))
            self.assertEqual(unframe(padded), False, "While padding {}".format(x))

    def test_cobs_empty_pading_frame_does_not_return_data(self):
        # Create a COBS empty frame
        padded = pad_payload(b'', 2)
        self.assertEqual(unframe(padded), None)

    #@unittest.skip
    def test_udp(self):
        modem = WlModemSimulator(0, 0, 0)
        modem.connect()
        sock = WlUDPSocket(modem, debug=True, sleep_time=0)

        #data = b"There is an art, it says, or rather, a knack to flying. The knack lies in learning how to throw yourself at the ground and miss"
        data = b"There is an art, it says, or rather, a knack to flying."
        sock.send(data)

        got = None
        timeout = 1000
        while timeout > 0:
            got = sock.receive()
            if got is not None:
                break
            timeout -= 1
            time.sleep(0.01)

        self.assertEqual(got, data)

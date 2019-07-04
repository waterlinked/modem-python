""" Unittest """
import unittest
import time
from wlmodem.simulator import WlModemSimulator


class TestWlModemSimulator(unittest.TestCase):
    def _make_one(self):
        return WlModemSimulator()

    def test_connect_with_response_is_success(self):
        modem = self._make_one()
        self.assertTrue(modem.connect())

    def test_cmd_configure_works(self):
        modem = self._make_one()
        success = modem.cmd_configure("a", 4)
        self.assertTrue(success)
        # Link is down after reconfigure
        diag = modem.cmd_get_diagnostic()
        self.assertFalse(diag.get("link_up"))

    def test_cmd_queue_length_works(self):
        modem = self._make_one()
        modem.connect()
        # Add 1 packet to queue
        modem.cmd_queue_packet(b"12345678")
        _len = modem.cmd_get_queue_length()
        self.assertEqual(_len, 1)
        # Flush queue
        success = modem.cmd_flush_queue()
        self.assertTrue(success)
        # Queue length should now be 0
        _len = modem.cmd_get_queue_length()
        self.assertEqual(_len, 0)

    def test_cmd_diagnostic_works(self):
        modem = self._make_one()
        diag = modem.cmd_get_diagnostic()
        expect = dict(link_up=True, pkt_cnt=0, pkt_loss_cnt=0, bit_error_rate=3.5)
        self.assertDictEqual(diag, expect)

    def test_cmd_version(self):
        modem = self._make_one()
        ver = modem.cmd_get_version()
        self.assertListEqual(ver, [1, 0, 1])

    def test_get_data(self):
        modem = self._make_one()
        modem.connect()
        modem.cmd_queue_packet(b"12345678")
        modem._next_packet_time = time.time() + 0.01  # Don't want to wait in the unit test
        # The packet is not available yet
        data = modem.get_data_packet(timeout=0.0)
        self.assertEqual(data, None)
        time.sleep(0.01)
        # Now it should be
        data = modem.get_data_packet(timeout=0.5)
        self.assertEqual(data, b"12345678")

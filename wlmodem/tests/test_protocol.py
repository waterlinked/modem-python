""" Unittest """
import unittest
import sys
from wlmodem.protocol import WlProtocolParser, WlModemBase, ModemSentence, CMD_GET_VERSION
from wlmodem.protocol import WlModemGenericError, WlProtocolChecksumError, WlProtocolParseError
from wlmodem.simulator import MockIODev

class TestProtoParser(unittest.TestCase):
    def test_parser(self):
        parser = WlProtocolParser()
        res = parser.do_frame(CMD_GET_VERSION)
        self.assertEqual(res, b"wcv\n")

    def test_parsing(self):
        parser = WlProtocolParser()
        res = parser.parse(b'wrv,1,0,1*44')
        self.assertIsInstance(res, ModemSentence)
        self.assertEqual(res.cmd, ord("v"))
        self.assertEqual(res.dir, ord("r"))
        self.assertEqual(res.options, [b'1', b'0', b'1'])

    def test_parsing_packet(self):
        parser = WlProtocolParser()
        res = parser.parse(b'wrp,8,12345678*83')
        self.assertIsInstance(res, ModemSentence)
        self.assertEqual(res.cmd, ord("p"))
        self.assertEqual(res.dir, ord("r"))
        self.assertEqual(res.options, [b'8', b'12345678'])

    def test_parsing_packet_accepts_newlines(self):
        parser = WlProtocolParser()
        res = parser.parse(b'wrp,8,\n\n\n\n\n\n\n*93')
        self.assertIsInstance(res, ModemSentence)
        self.assertEqual(res.cmd, ord("p"))
        self.assertEqual(res.dir, ord("r"))
        self.assertEqual(res.options, [b'8', b'\n\n\n\n\n\n\n'])


class TestWlModemLowLevel(unittest.TestCase):
    def _make_one(self, data):
        dev = MockIODev(data)
        modem = WlModemBase(dev)
        return modem, dev

    def test_binary_accepts_newline_in_payload(self):
        modem, _ = self._make_one(b"wrp,8,Hi\nThere\n")
        pkt = modem.get_packet()
        self.assertIsInstance(pkt, ModemSentence)
        self.assertEqual(pkt.cmd, ord("p"))
        self.assertEqual(pkt.dir, ord("r"))
        self.assertEqual(pkt.options, [b'8', b'Hi\nThere'])

    def test_partial_packet_is_accepted(self):
        modem, dev = self._make_one(b"wrp,8,Hello")
        pkt = modem.get_packet()
        self.assertEqual(pkt, None)

        dev.feed(b"Sea\n")
        pkt = modem.get_packet()
        self.assertIsInstance(pkt, ModemSentence)
        self.assertEqual(pkt.cmd, ord("p"))
        self.assertEqual(pkt.dir, ord("r"))
        self.assertEqual(pkt.options, [b'8', b'HelloSea'])

    def test_checksum_is_parsed(self):
        modem, _ = self._make_one(b"wrp,8,HelloSea*58\n\n\n")
        pkt = modem.get_packet()
        self.assertIsInstance(pkt, ModemSentence)
        self.assertEqual(pkt.cmd, ord("p"))
        self.assertEqual(pkt.dir, ord("r"))
        self.assertEqual(pkt.options, [b'8', b'HelloSea'])

    def test_invaid_checksum_is_parsed_detected(self):
        modem, _ = self._make_one(b"wrp,8,HelloSea*ff\n\n\n")
        self.assertRaises(WlProtocolChecksumError, modem.get_packet)

    def test_parsing_invalid_packet_is_detected(self):
        modem, _ = self._make_one(b"wzx\n")
        self.assertRaises(WlProtocolParseError, modem.get_packet)

    def test_any_newline_is_accepted(self):
        modem, _ = self._make_one(b"wcv\r\nwcv\rwcv\n")

        pkt = modem.get_packet()
        self.assertIsInstance(pkt, ModemSentence)

        pkt = modem.get_packet()
        self.assertIsInstance(pkt, ModemSentence)

        pkt = modem.get_packet()
        self.assertIsInstance(pkt, ModemSentence)


class TestWlModem(unittest.TestCase):
    def _make_one(self, data):
        dev = MockIODev(data)
        modem = WlModemBase(dev)
        return modem, dev

    def test_connect_without_response_fails(self):
        modem, _ = self._make_one(b"")
        self.assertFalse(modem.connect())

    def test_connect_with_response_is_success(self):
        modem, _ = self._make_one(b"wrv,1,0,1\nwrn,8\n")
        self.assertTrue(modem.connect())
        self.assertEqual(modem.payload_size, 8)

    def test_cmd_configure_works(self):
        modem, _ = self._make_one(b"wrs,a\n")
        success = modem.cmd_configure("a", 4)
        self.assertTrue(success)

    def test_cmd_configure_invalid_fails(self):
        modem, _ = self._make_one(b"wr?\n")
        success = modem.cmd_configure("a", 4, timeout=0.01)
        self.assertFalse(success)

    def test_cmd_queue_length_works(self):
        modem, _ = self._make_one(b"wrl,8\n")
        _len = modem.cmd_get_queue_length()
        self.assertEqual(_len, 8)

    def test_cmd_flush_works(self):
        modem, _ = self._make_one(b"wrf,a\n")
        success = modem.cmd_flush_queue()
        self.assertTrue(success)

    def test_cmd_flush_fails_is_detected(self):
        modem, _ = self._make_one(b"wrf,n\n")
        success = modem.cmd_flush_queue()
        self.assertFalse(success)

    def test_cmd_diagnostic_works(self):
        modem, _ = self._make_one(b"wrd,n,1,2,3.0\n")
        diag = modem.cmd_get_diagnostic()
        expect = dict(link_up=False, pkt_cnt=1, pkt_loss_cnt=2, bit_error_rate=3.0)
        self.assertDictEqual(diag, expect)

    def test_cmd_version(self):
        modem, _ = self._make_one(b"wrv,1,2,3\n")
        ver = modem.cmd_get_version()
        self.assertListEqual(ver, [1, 2,3])

    def test_cmd_queue_packet(self):
        modem, _ = self._make_one(b"wrq,a\n")
        modem.payload_size = 8  # Faking that we are connected
        success = modem.cmd_queue_packet(b"12345678")
        self.assertTrue(success)

    def test_cmd_queue_packet_invalid_size_fails(self):
        modem, _ = self._make_one(b"wrq,a\n")
        modem.payload_size = 8  # Faking that we are connected
        self.assertRaises(WlModemGenericError, modem.cmd_queue_packet, b"1234567")
        if sys.version_info > (3, 0):
            self.assertRaises(WlModemGenericError, modem.cmd_queue_packet, "12345678")

    def test_get_data(self):
        modem, _ = self._make_one(b"wrp,8,12345678\n")
        modem.payload_size = 8  # Faking that we are connected
        data = modem.get_data_packet(timeout=0.01)
        self.assertEqual(data, b"12345678")

    def test_get_data_is_queued_while_other_command_is_run(self):
        modem, _ = self._make_one(b"wrp,8,12345678\nwrl,8\n")
        _len = modem.cmd_get_queue_length()
        self.assertEqual(_len, 8)
        data = modem.get_data_packet()
        self.assertEqual(data, b"12345678")

    def test_non_blocking_get_data_with_no_data(self):
        modem, _ = self._make_one(b"")
        data = modem.get_data_packet(timeout=0)
        self.assertEqual(data, None)

    def test_non_blocking_get_data_with_data(self):
        modem, _ = self._make_one(b"wrp,8,12345678\n")
        data = modem.get_data_packet(timeout=0)
        self.assertEqual(data, b"12345678")

    # def test_non_blocking_get_data_with_data(self):
    #     modem, _ = self._make_one(b"wrp,8,12345678\n")
    #     data = modem.get_data_packet(timeout=0)
    #     self.assertEqual(data, b"12345678")


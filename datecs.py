import socket
import serial
from enum import Enum

PREAMBLE = b'\x01'
POSTAMBLE = b'\x05'
TERMINATOR = b'\x03'
SEPARATOR = b'\x04'

NAK = 0x15
SYN = 0x16
TRM = 0x03

SEQ_START = 0x20
SEQ_MAX = 0xff

CMD_PROGRAMMING = 0xff          # X Only: Programming {Name}<SEP>{Index}<SEP>{Value}<SEP>
CMD_GET_DIAGNOSTIC_INFO = 0x5a  # Diagnostic information

CMD_GET_DATE_TIME = 0x3e        #
CMD_SET_DATETIME = 0x3d         # OLD: DD-MM-YY HH:MM[:SS]; X: DD-MM-YY hh:mm:ss DST<SEP>


class Protocol(Enum):
    OLD = 1
    X = 2

    @classmethod
    def encode_word(cls, w) -> bytearray:
        b2 = w.to_bytes(2, "big")
        b4 = bytearray()
        b4.append(0x30 + (b2[0] >> 4))
        b4.append(0x30 + (b2[0] & 0xf))
        b4.append(0x30 + (b2[1] >> 4))
        b4.append(0x30 + (b2[1] & 0xf))
        return b4

    @classmethod
    def get_status(cls, packet):
        sep = packet.find(SEPARATOR)
        if sep > 0:
            return packet[sep+1:sep + 8]
        else:
            return None

    def calc_bcc(self, packet) -> bytearray:
        return self.encode_word(sum(packet) & 0xffff)

    def format_packet(self, seq, cmd, data) -> bytearray:
        seq_byte = seq.to_bytes(1, "big")

        if self.value == 1:  # Protocol.OLD
            packet_len = (0x24 + len(data)).to_bytes(1, "big")
            cmd_code = cmd.to_bytes(1, "big")
        else:                # Protocol.X
            packet_len = self.encode_word(0x002a + len(data))
            cmd_code = self.encode_word(cmd)

        packet = packet_len + seq_byte + cmd_code + data + POSTAMBLE
        bcc = self.calc_bcc(packet)

        return PREAMBLE + packet + bcc + TERMINATOR

    def get_data(self, packet):
        sep = packet.find(SEPARATOR)
        if sep > 0:
            if self.value == 1:  # Protocol.OLD
                return packet[4:sep].decode()
            else:                # Protocol.X
                return packet[12:sep - 1].decode()
        else:
            return None


class FiscalResponse:
    def bit_on(self, x, n):
        return self.status_bytes[x] & 1 << n-1 != 0

    def __init__(self, packet, protocol):
        self.data = protocol.get_data(packet)
        self.status_bytes = protocol.get_status(packet)
        self.bcc = None
        self.ok = not (self.general_error() or self.cover_open())
        self.error_code = 0
        self.error_message = ''

    def cover_open(self):
        return self.bit_on(0, 6)

    def general_error(self):
        return self.bit_on(0, 5)

    def mechanism_failure(self):
        return self.bit_on(0, 4)

    def rtc_not_synchronized(self):
        return self.bit_on(0, 2)

    def invalid_command(self):
        return self.bit_on(0, 1)

    def syntax_error(self):
        return self.bit_on(0, 0)

    def command_not_permitted(self):
        return self.bit_on(1, 1)

    def overflow_during_command(self):
        return self.bit_on(1, 0)

    def nonfiscal_receipt_open(self):
        return self.bit_on(2, 5)

    def fiscal_receipt_open(self):
        return self.bit_on(2, 3)

    def end_of_paper(self):
        return self.bit_on(2, 0)


class NakException(Exception):
    pass


class SerialConnector:

    def __init__(self, port, speed):
        self.port = port
        self.speed = speed
        self.com = serial.Serial()

    def connect(self):
        self.com.port = self.port
        self.com.baudrate = self.speed
        self.com.timeout = 0.3  # 300ms red timeout
        self.com.open()
        return self.com.is_open

    def write_data(self, data):
        self.com.write(data)
        self.com.flush()

    def read_data(self):
        return self.com.read()

    def disconnect(self):
        self.com.close()


class EthernetConnector:

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.address = (self.ip, self.port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.sock.settimeout(2.0)  # 2sec connection timeout
        self.sock.connect(self.address)

    def write_data(self, data):
        self.sock.sendall(data)
        self.sock.settimeout(0.5)  # 500ms read timeout

    def read_data(self):
        return self.sock.recv(1024)

    def disconnect(self):
        self.sock.close()


class FiscalDevice:

    def __init__(self, connector, protocol):
        self.connector = connector
        self.protocol = protocol
        self.seq = SEQ_START
        self.last_packet = None
        self.last_packet = None
        self.connected = False

    def connect(self):
        self.connector.connect()
        self.connected = True
        return True

    def disconnect(self):
        self.connector.disconnect()
        self.connected = False

    def send_last_packet(self):
        self.connector.write_data(self.last_packet)

    def wait_response(self):
        response = bytearray()
        terminated = False
        while not terminated:
            rec = self.connector.read_data()
            for b in rec:
                if b == SYN:
                    continue
                if b == NAK:
                    raise NakException
                if b == TRM:
                    terminated = True

                response.append(b)

        return response

    def execute(self, cmd, data=b''):
        if not self.connected:
            raise Exception('Not connected')

        if self.seq >= SEQ_MAX:
            self.seq = SEQ_START
        else:
            self.seq += 1

        self.last_packet = self.protocol.format_packet(self.seq, cmd, data)

        self.send_last_packet()     # send cmd
        try:
            response_data = self.wait_response()
        except NakException:  # NAK from ECR
            self.send_last_packet()  # repeat last cmd (with same seq)
            response_data = self.wait_response()

        return FiscalResponse(response_data, self.protocol)


if __name__ == '__main__':
    fd = FiscalDevice(EthernetConnector('192.168.0.36', 4999), Protocol.X)
    if fd.connect():
        try:
            print('\nEthernet connected')
            fr = fd.execute(CMD_PROGRAMMING, b'IDnumber\t\t\t')
            print('IDnumber:', fr.data)

            fr = fd.execute(CMD_GET_DATE_TIME)
            print('DateTime:', fr.data)
        finally:
            fd.disconnect()

    fd = FiscalDevice(SerialConnector('COM1', 115200), Protocol.OLD)
    if fd.connect():
        try:
            print('\nSerial connected')
            fr = fd.execute(CMD_GET_DIAGNOSTIC_INFO)
            print('Diagnostic Info:', fr.data)

            fr = fd.execute(CMD_GET_DATE_TIME)
            print('DateTime:', fr.data)

            print('Status bytes:', fr.status_bytes)
            print('Cover is open:', fr.cover_open())
        finally:
            fd.disconnect()

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

CMD_PROGRAMMING = 0xff          # Programming {Name}<SEP>{Index}<SEP>{Value}<SEP>
CMD_GET_DIAGNOSTIC_INFO = 0x5a  # Diagnostic information

CMD_GET_DATE_TIME = 0x3e        #
CMD_SET_DATETIME = 0x3d         # OLD: DD-MM-YY HH:MM[:SS]; X: DD-MM-YY hh:mm:ss DST<SEP>


class Protocol(Enum):
    OLD = 1
    X = 2


class NakException(Exception):
    pass


class FiscalResponse:
    def __init__(self, packet, protocol):
        sep = packet.find(SEPARATOR)
        if sep > 0:
            if protocol == Protocol.X:
                self.data = packet[12:sep-1].decode()
            else:
                self.data = packet[4:sep].decode()
        else:
            self.data = None

        self.bcc = None
        self.ok = False
        self.error_code = 0
        self.error_message = ''


class Connector:
    def connect(self):
        raise NotImplementedError

    def write_data(self, data):
        raise NotImplementedError

    def read_data(self) -> bytearray:
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError


class SerialConnector(Connector):

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

    def read_data(self) -> bytearray:
        response = bytearray()
        terminated = False
        while not terminated:
            rec = self.com.read()
            for b in rec:
                if b == SYN:
                    continue
                if b == NAK:
                    raise NakException
                if b == TRM:
                    terminated = True

                response.append(b)

        # print(response)
        return response

    def disconnect(self):
        self.com.close()


class EthernetConnector(Connector):

    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.address = (self.ip, self.port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.sock.settimeout(2.0)   # 2sec connection timeout
        self.sock.connect(self.address)

    def write_data(self, data):
        self.sock.sendall(data)
        self.sock.settimeout(0.5)   # 500ms i/o timeout

    def read_data(self) -> bytearray:
        response = bytearray()
        terminated = False
        while not terminated:
            rec = self.sock.recv(1024)
            for b in rec:
                if b == SYN:
                    continue
                if b == NAK:
                    raise NakException
                if b == TRM:
                    terminated = True

                response.append(b)

        return response

    def disconnect(self):
        self.sock.close()


def calc_bcc(packet):
    return sum(packet) & 0xffff


def encode_word(w) -> bytearray:
    b2 = w.to_bytes(2, "big")
    b4 = bytearray()
    b4.append(0x30 + (b2[0] >> 4))
    b4.append(0x30 + (b2[0] & 0xf))
    b4.append(0x30 + (b2[1] >> 4))
    b4.append(0x30 + (b2[1] & 0xf))
    return b4


class FiscalDevice:

    def __init__(self, connector, protocol=Protocol.X):
        self.connector = connector
        self.protocol = protocol
        self.seq = 0x20
        self.last_packet = None
        self.last_packet = None
        self.connected = False

    def format_packet(self, cmd, data) -> bytearray:
        seq_byte = self.seq.to_bytes(1, "big")
        packet_len = (0x24 + len(data)).to_bytes(1, "big")
        cmd_byte = cmd.to_bytes(1, "big")
        packet = packet_len + seq_byte + cmd_byte + data + POSTAMBLE
        bcc = calc_bcc(packet)
        return PREAMBLE + packet + encode_word(bcc) + TERMINATOR

    def format_packet_x(self, cmd, data) -> bytearray:
        seq_byte = self.seq.to_bytes(1, "big")
        packet_len = 0x002A + len(data)
        packet = encode_word(packet_len) + seq_byte + encode_word(cmd) + data + POSTAMBLE
        bcc = calc_bcc(packet)
        return PREAMBLE + packet + encode_word(bcc) + TERMINATOR

    def connect(self):
        self.connector.connect()
        self.connected = True
        return True

    def disconnect(self):
        self.connector.disconnect()
        self.connected = False
        return True

    def execute(self, cmd, data=b''):

        if not self.connected:
            raise Exception('Not connected')

        if self.seq > 0xff:
            self.seq = 0x20
        else:
            self.seq += 1

        if self.protocol == Protocol.OLD:
            self.last_packet = self.format_packet(cmd, data)
        else:
            self.last_packet = self.format_packet_x(cmd, data)

        self.connector.write_data(self.last_packet)         # send
        try:
            response = self.connector.read_data()
        except NakException:                                # NAK from ECR
            self.connector.write_data(self.last_packet)     # repeat last cmd with same seq
            response = self.connector.read_data()

        return FiscalResponse(response, self.protocol)


if __name__ == '__main__':
    fd = FiscalDevice(EthernetConnector('192.168.8.100', 4999), Protocol.X)
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
        finally:
            fd.disconnect()

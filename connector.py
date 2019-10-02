import socket
import serial
from protocol import (SYN, NAK, TRM)


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

        return response

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

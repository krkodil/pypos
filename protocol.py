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


class DatecsProtocol(Enum):
    OLD = 1
    X = 2

    def __init__(self, value):
        self.seq = SEQ_START
        if self.value == 1:  # OLD
            self.SEP = ','
        else:                # X
            self.SEP = '\t'

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
        return packet[sep + 1:sep + 8]

    def calc_bcc(self, packet) -> bytearray:
        return self.encode_word(sum(packet) & 0xffff)

    def format_packet(self, cmd, data) -> bytearray:

        if self.seq >= SEQ_MAX:
            self.seq = SEQ_START
        else:
            self.seq += 1

        seq_byte = self.seq.to_bytes(1, "big")

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
        if self.value == 1:  # Protocol.OLD
            return packet[4:sep].decode()
        else:                # Protocol.X
            return packet[12:sep - 1].decode()

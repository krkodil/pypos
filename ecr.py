from datetime import datetime

from protocol import DatecsProtocol
from connector import NakException
from response import FiscalResponse

CMD_PROGRAMMING = 0xff          # X Only: Programming {Name}<SEP>{Index}<SEP>{Value}<SEP>
CMD_GET_DIAGNOSTIC_INFO = 0x5a  # Diagnostic information

CMD_GET_DATE_TIME = 0x3e  #
CMD_SET_DATETIME = 0x3d   # OLD: DD-MM-YY HH:MM[:SS]; X: DD-MM-YY hh:mm:ss DST<SEP>

CMD_OPEN_FISCAL_RECEIPT = 0x30  # {OpCode}<SEP>{OpPwd}<SEP>{NSale}<SEP>{TillNmb}<SEP>{Invoice}<SEP>


class FiscalDevice:

    def __init__(self, connector, protocol):
        self.connector = connector
        self.protocol = protocol
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

    def execute(self, cmd, data=b''):
        if not self.connected:
            raise Exception('Not connected')

        self.last_packet = self.protocol.format_packet(cmd, data)

        self.connector.write_data(self.last_packet)  # send cmd
        try:
            response_data = self.connector.read_data()
        except NakException:  # NAK from ECR
            self.connector.write_data(self.last_packet)  # repeat last cmd with same seq
            response_data = self.connector.read_data()

        return FiscalResponse(response_data, self.protocol)

    def get_date_time(self):
        fr = self.execute(CMD_GET_DATE_TIME)
        if self.protocol == DatecsProtocol.X:
            return datetime.strptime(fr.data, '%d-%m-%y %H:%M:%S DST')  # 02-10-19 21:29:42 DST
        elif self.protocol == DatecsProtocol.OLD:
            return datetime.strptime(fr.data, '%d-%m-%y %H:%M:%S')  # 02-10-19 21:29:42

    # Syntax 1: {OpCode}<SEP>{OpPwd}<SEP>{TillNmb}<SEP>{Invoice}<SEP>
    # Syntax 2: {OpCode}<SEP>{OpPwd}<SEP>{NSale}<SEP>{TillNmb}<SEP>{Invoice}<SEP>
    def open_fiscal_receipt(self, operator, password, work_place, n_sale):
        data = str(operator) + self.protocol.SEP + str(password) + self.protocol.SEP
        if n_sale is not None:
            data +=  n_sale + self.protocol.SEP
        data += str(work_place) + self.protocol.SEP + self.protocol.SEP
        fr = self.execute(CMD_OPEN_FISCAL_RECEIPT, bytearray(data))
        return fr.ok

    # Syntax: {OpCode}<SEP>{OpPwd}<SEP>{TillNmb}<SEP>{Storno}<SEP>{DocNum}<SEP>{DateTime}<SEP>
    #         {FMNumber}<SEP>{Invoice}<SEP>{ToInvoice}<SEP>{Reason}<SEP>{NSale}<SEP>
    def open_storno_document(self):
        pass

    def print(self, bon):
        if bon.storno_reason is None:
            self.open_fiscal_receipt(bon.operator, bon.password, bon.work_place, bon.n_sale)
        else:
            self.open_storno_document()


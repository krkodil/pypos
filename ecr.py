from datetime import datetime

from protocol import DatecsProtocol
from errors import DatecsErrors
from connector import NakException
from response import FiscalResponse

NAK = 0x15
SYN = 0x16
TRM = 0x03

CMD_PROGRAMMING = 0xff          # X Only: Programming {Name}<SEP>{Index}<SEP>{Value}<SEP>
CMD_GET_DIAGNOSTIC_INFO = 0x5a  # Diagnostic information

CMD_GET_DATE_TIME = 0x3e  #
CMD_SET_DATE_TIME = 0x3d   # OLD: DD-MM-YY HH:MM[:SS]; X: DD-MM-YY hh:mm:ss DST<SEP>

CMD_OPEN_FISCAL_RECEIPT = 0x30  # {OpCode}<SEP>{OpPwd}<SEP>{NSale}<SEP>{TillNmb}<SEP>{Invoice}<SEP>


class DatecsError(Exception):
    def __init__(self, function, code, message):
        self.function = function
        self.code = code
        self.message = message
        super().__init__(function + ': ' + str(code) + ': ' + message)


class DatecsFiscalDevice:

    def __init__(self, connector, protocol):
        self.connector = connector
        self.protocol = protocol
        self.error_list = DatecsErrors()
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

        self.last_packet = self.protocol.format_packet(cmd, data)

        self.send_last_packet()  # send cmd
        try:
            response_data = self.wait_response()
        except NakException:  # NAK from ECR
            self.send_last_packet()  # repeat last cmd (with same seq)
            response_data = self.wait_response()
        return FiscalResponse(response_data, self.protocol)

    def get_date_time(self):
        fr = self.execute(CMD_GET_DATE_TIME)
        if fr.no_errors(0, self.error_list):
            if self.protocol == DatecsProtocol.X:
                return datetime.strptime(fr.values[1], '%d-%m-%y %H:%M:%S DST')  # 02-10-19 21:29:42 DST
            elif self.protocol == DatecsProtocol.OLD:
                return datetime.strptime(fr.values[1], '%d-%m-%y %H:%M:%S')  # 02-10-19 21:29:42
        else:
            raise DatecsError('GET_DATE_TIME', fr.error_code, fr.error_message)

    def set_date_time(self, date_time):
        # OLD: DD-MM-YY HH:MM[:SS];
        # X: DD-MM-YY hh:mm:ss DST<SEP>
        if self.protocol == DatecsProtocol.X:
            data = date_time.strftime('%d-%m-%y %H:%M:%S DST')
        else:
            data = date_time.strftime('%d-%m-%y %H:%M:%S')

        data = data + self.protocol.SEP
        fr = self.execute(CMD_SET_DATE_TIME, bytearray(data, 'ascii'))
        if fr.no_errors(0, self.error_list):
            return fr.ok
        else:
            raise DatecsError('SET_DATE_TIME', fr.error_code, fr.error_message)

    def open_fiscal_receipt(self, operator, password, work_place, n_sale):
        # Syntax 1: {OpCode}<SEP>{OpPwd}<SEP>{TillNmb}<SEP>{Invoice}<SEP>
        # Syntax 2: {OpCode}<SEP>{OpPwd}<SEP>{NSale}<SEP>{TillNmb}<SEP>{Invoice}<SEP>
        data = str(operator) + self.protocol.SEP + str(password) + self.protocol.SEP
        if n_sale is not None:
            data += n_sale + self.protocol.SEP
        data += str(work_place) + self.protocol.SEP + self.protocol.SEP

        fr = self.execute(CMD_OPEN_FISCAL_RECEIPT, bytearray(data))
        if fr.no_errors(0, self.error_list):
            return fr.ok
        else:
            raise DatecsError('OPEN_FISCAL_RECEIPT', fr.error_code, fr.error_message)

    # Syntax: {OpCode}<SEP>{OpPwd}<SEP>{TillNmb}<SEP>{Storno}<SEP>{DocNum}<SEP>{DateTime}<SEP>
    #         {FMNumber}<SEP>{Invoice}<SEP>{ToInvoice}<SEP>{Reason}<SEP>{NSale}<SEP>
    def open_storno_document(self):
        pass    # todo ...

    def print(self, bon):
        if bon.storno_reason is None:
            self.open_fiscal_receipt(bon.operator, bon.password, bon.work_place, bon.n_sale)
        else:
            self.open_storno_document()

        # todo: add articles

        # todo: close bon

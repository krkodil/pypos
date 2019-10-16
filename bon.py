from enum import Enum


class PayMode(Enum):
    CASH = 0,
    CARD = 1,
    ON_DELIVERY = 2

    def __str__(self):
        return str(self.value[0])


class Product:
    def __init__(self, name, quantity, price, unit='', tax_cd=2):
        self.name = name
        self.quantity = round(quantity, 3)
        self.price = round(price, 2)
        self.unit = unit
        self.tax_cd = tax_cd

    def total(self):
        return round(self.quantity * self.price, 2)


class FiscalBon:

    def __init__(self, operator, password, work_place,
                 n_sale=None, storno_reason=None, storno_doc=None, storno_dt=None, fm_number=None):
        self.operator = operator
        self.password = password
        self.work_place = work_place
        self.n_sale = n_sale
        self.storno_reason = storno_reason
        self.storno_doc = storno_doc
        self.storno_dt = storno_dt
        self.fm_number = fm_number
        self.products = []
        self.total = 0
        self.pay_mode = PayMode.CASH
        self.payed = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def add(self, product):
        self.products.append(product)
        self.total += product.total()

    def close(self, amount, pay_mode=PayMode.CASH):
        if amount < self.total:
            raise Exception('Insufficient amount')
        self.pay_mode = pay_mode
        self.payed = amount

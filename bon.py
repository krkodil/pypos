from enum import Enum


class Pay(Enum):
    CASH = 0,
    CARD = 1,
    ON_DELIVERY = 2


class Article:
    def __init__(self, name, quantity, price, measure=b''):
        self.name = name
        self.quantity = round(quantity, 3)
        self.price = round(price, 2)
        self.measure = measure


class FiscalBon:

    def __init__(self, operator, password, work_place, n_sale=None, storno_reason=None, storno_doc=None, storno_dt=None):
        self.operator = operator
        self.password = password
        self.work_place = work_place
        self.n_sale = n_sale
        self.storno_reason = storno_reason
        self.storno_doc = storno_doc
        self.storno_dt = storno_dt
        self.articles = []
        self.total = 0
        self.pay_type = Pay.CASH

    def add(self, article):
        self.articles.append(article)
        self.total += round(article.quantity*article.price, 2)

    def close(self, pay_type, amount):
        self.pay_type = pay_type
        if amount < self.total:
            raise Exception('Insufficient amount')

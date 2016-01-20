from datetime import date
from datetime import datetime


def to_year(values):
    for value in values:
        if not isinstance(value, date) or isinstance(value, datetime):
            continue
        yield str(value.year)

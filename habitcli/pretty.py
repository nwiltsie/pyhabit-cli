#Shamelessly modified from https://github.com/imtapps/django-pretty-times/blob/master/pretty_times/pretty.py

import datetime

def date(time):

    if isinstance(time, datetime.datetime):
        now = datetime.datetime.now(time.tzinfo)
        dt = True
    elif isinstance(time, datetime.date):
        now = datetime.datetime.now().date()
        dt = False
    else:
        raise Exception("Pretty needs a datetime or a date")

    if time > now:
        past = False
        diff = time - now
    else:
        past = True
        diff = now - time

    days = diff.days

    if days is 0 and dt:
        return get_small_increments(diff.seconds, past)
    else:
        return get_large_increments(days, past)


def get_small_increments(seconds, past):
    if seconds < 10:
        result = _('just now')
    elif seconds < 60:
        result = _pretty_format(seconds, 1, 'seconds', past)
    elif seconds < 120:
        result = past and 'a minute ago' or 'in a minute'
    elif seconds < 3600:
        result = _pretty_format(seconds, 60, 'minutes', past)
    elif seconds < 7200:
        result = past and 'an hour ago' or 'in an hour'
    else:
        result = _pretty_format(seconds, 3600, 'hours', past)
    return result


def get_large_increments(days, past):
    if days == 0:
        result = 'today'
    elif days == 1:
        result = past and 'yesterday' or 'tomorrow'
    elif days < 7:
        result = _pretty_format(days, 1, 'days', past)
    elif days < 14:
        result = past and 'last week' or 'next week'
    elif days < 31:
        result = _pretty_format(days, 7, 'weeks', past)
    elif days < 61:
        result = past and 'last month' or 'next month'
    elif days < 365:
        result = _pretty_format(days, 30, 'months', past)
    elif days < 730:
        result = past and 'last year' or 'next year'
    else:
        result = _pretty_format(days, 365, 'years', past)
    return result


def _pretty_format(diff_amount, units, text, past):
    pretty_time = (diff_amount + units / 2) / units
    if past:
        base = "%(amount)d %(quantity)s ago"
    else:
        base = "In %(amount)d %(quantity)s"
    return base % dict(amount=pretty_time, quantity=text)

from nose.tools import *
import habitcli

def setup():
    print "SET UP!"

def teardown():
    print "TEAR DOWN!"

@with_setup(setup, teardown)
def test_serializing():
    import datetime
    test_date = datetime.datetime.now()
    date_str = habitcli.serialize_date(test_date)
    deser_date = habitcli.deserialize_date(date_str)
    assert_equals(test_date, deser_date) 

@with_setup(setup, teardown)
def test_stats():
    habitcli.print_stat_bar()

@with_setup(setup, teardown)
def test_ls():
    habitcli.list_todos()

def test_basic():
    return
    import random
    import datetime
    year = random.choice(range(2000,2100))
    month = random.choice(range(1,12))
    day = random.choice(range(1,28))
    hour = random.choice(range(0,23))
    minute = random.choice(range(0,60))

    date_str = "%s/%s/%s %s:%s" % (month, day, year, hour, minute)
    dt_obj = habitcli.parse_datetime_from_date_str(date_str)

    print "I RAN!"

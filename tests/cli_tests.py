from nose.tools import *
import habitcli

class HabitTest:
    def setup(self):
        self.hcli = habitcli.HabitCLI()
        print "SET UP!"

    def teardown(self):
        print "TEAR DOWN!"

    def test_serializing(self):
        import datetime
        test_date = datetime.datetime.now()
        date_str = habitcli.utils.serialize_date(test_date)
        deser_date = habitcli.utils.deserialize_date(date_str)
        assert_equals(test_date, deser_date)

    def test_stats(self):
        hcli.print_stat_bar()

    def test_ls(self):
        hcli.list_todos()

    def test_basic(self):
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

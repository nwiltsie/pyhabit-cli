"""Utility functions for habitcli."""

import dateutil.parser
import os
import pytz
import yaml

from parsedatetime import Calendar
from tzlocal import get_localzone

# http://code.activestate.com/recipes/541096-prompt-the-user-for-confirmation/
def confirm(prompt=None, resp=False):
    """Prompts for yes or no response from the user. Returns True for yes and
    False for no.

    'resp' should be set to the default value assumed by the caller when
    user simply types ENTER.

    >>> confirm(prompt='Create Directory?', resp=True)
    Create Directory? [y]|n:
    True
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y:
    False
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y: y
    True

    """

    if prompt is None:
        prompt = 'Confirm'

    if resp:
        prompt = '%s [%s]|%s: ' % (prompt, 'y', 'n')
    else:
        prompt = '%s [%s]|%s: ' % (prompt, 'n', 'y')

    while True:
        ans = raw_input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print 'please enter y or n.'
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False

def serialize_date(date_obj):
    """Serialize a datetime object to plain text."""
    return yaml.dump(date_obj, default_flow_style=False)

def deserialize_date(date_str):
    """Deserialize a datetime object from plain text."""
    def timestamp_constructor(loader, node):
        """A better YAML datetime parser that is timezone aware."""
        return dateutil.parser.parse(node.value)

    yaml.add_constructor(u'tag:yaml.org,2002:timestamp', timestamp_constructor)
    return yaml.load(date_str)

def parse_datetime_from_date_str(date_string):
    """Parse a timetime object from a natural language string."""
    cal = Calendar()
    unaware_dt = cal.nlp(date_string)
    if not unaware_dt:
        raise Exception("Due date %s unclear" % date_string)
    else:
        code = unaware_dt[0][1]
        unaware_dt = unaware_dt[0][0]
        # If no time is supplied, assume 6pm
        if code == 1:
            unaware_dt = unaware_dt.replace(hour=18)
            unaware_dt = unaware_dt.replace(minute=0)
            unaware_dt = unaware_dt.replace(second=0)
    if os.environ.get('HABIT_TZ'):
        localtz = pytz.timezone(os.environ.get('HABIT_TZ'))
    else:
        localtz = get_localzone()
    aware_dt = localtz.localize(unaware_dt)
    return aware_dt

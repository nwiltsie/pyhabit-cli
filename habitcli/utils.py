"""Utility functions for habitcli."""

import ConfigParser
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


def make_unambiguous_date_str(datetimeobj):
    return datetimeobj.strftime('%a %D at %H:%M')


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


def get_default_config_filename():
    """Return the fully-expanded default config file path."""
    return os.path.join(os.path.expanduser("~"), ".habitrc")


def read_config(config_filename=None):
    """Read the configuration file and return the results."""
    config_dict = {}

    if not config_filename:
        config_filename = get_default_config_filename()

    config = ConfigParser.SafeConfigParser()

    # If the config file does not exist, try to fetch the config details from
    # the environment; if that fails, write the default config file. Otherwise,
    # read the values from the config file (which may have just been written).
    if not os.path.exists(config_filename):
        if 'HABIT_USER_ID' in os.environ.keys() and \
                'HABIT_API_KEY' in os.environ.keys() and \
                'HABIT_TASKS' in os.environ.keys():
            config_dict['user_id'] = os.environ['HABIT_USER_ID']
            config_dict['api_key'] = os.environ['HABIT_API_KEY']
            tasks = [task.strip()
                     for task in os.environ['HABIT_TASKS'].split(",")]
            config_dict['tasks'] = tasks
            return config_dict
        else:
            print "No log file found, writing defaults to %s" % config_filename
            write_default_config_file(config_filename)

    config.read(config_filename)
    for key, value in config.items('HabitRPG'):
        config_dict[key] = value
    # Expand comma-separated string of tasks into list
    task_str = config_dict['tasks']
    config_dict['tasks'] = [task.split(':')[0].strip()
                            for task in task_str.split(',')]
    # Expand comma-separated string of task:color into a dict
    taskcolors = {}
    for task, color in [pair.split(':')
                        for pair in task_str.split(',')]:
        taskcolors[task.strip()] = color.strip()
    config_dict['taskcolors'] = taskcolors
    return config_dict


def write_default_config_file(config_filename=None):
    """Write a default configuration file."""
    if not config_filename:
        config_filename = get_default_config_filename()
    config = ConfigParser.SafeConfigParser()
    config.add_section('HabitRPG')
    config.set('HabitRPG', 'user_id', '-1')
    config.set('HabitRPG', 'api_key', '-1')
    config.set('HabitRPG', 'tasks', 'morning,afternoon,evening')
    with open(config_filename, 'wb') as config_file:
        config.write(config_file)


def _get_incomplete_todos():
    import habitcli
    user = habitcli.get_user()
    todos = [t for t in user['todos'] if 'completed' in t.keys()]
    todos = [t for t in todos if not t['completed']]
    return todos

#!/usr/bin/env python

# Standard library imports
import os
import pickle
import datetime
from collections import defaultdict

# Third party imports
import argh
import pretty
import pytz
from parsedatetime import Calendar
from tzlocal import get_localzone
from dateutil import parser as dtparser
from requests import ConnectionError
from colors import red, green, yellow, blue, faint
from fuzzywuzzy import process

# Same-project imports
from pyhabit import HabitAPI

CACHE_DIR = os.path.dirname(os.path.realpath(__file__))

def get_api():
    user = os.environ["HABIT_USER_ID"]
    api_key = os.environ["HABIT_API_KEY"]
    return HabitAPI(user, api_key)


def save_user(user):
    """Save the user object to a file."""
    pickle.dump(user, open(os.path.join(CACHE_DIR, ".habit.p"), 'wb'))

def load_user():
    """Load the user object from the cache."""
    return pickle.load(open(os.path.join(CACHE_DIR, ".habit.p"), 'rb'))

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

def get_user(api=None):
    """Get the user object from HabitRPG (if possible) or the cache."""
    try:
        if not api:
            api = get_api()
        user = api.user()
        save_user(user)
        user['cached'] = False
    except ConnectionError:
        user = load_user()
        user['cached'] = True

    # Add tag dictionaries to the user object
    tag_dict = defaultdict(lambda: "+missingtag")
    reverse_tag_dict = defaultdict(unicode)
    for tag in user['tags']:
        tag_dict[tag['id']] = tag['name']
        reverse_tag_dict[tag['name']] = tag['id']
    user['tag_dict'] = tag_dict
    user['reverse_tag_dict'] = reverse_tag_dict
    return user

def get_todo_str(user, todo, completed_faint=False, notes=False):
    """Get a nicely formatted and colored string describing a task."""
    color = lambda x: x
    todo_str = todo['text']
    for tag in todo['tags']:
        todo_str += " +%s" %user['tag_dict'][tag]
        if user['tag_dict'][tag] == 'urgent':
            color = red
        if user['tag_dict'][tag] == '15min':
            color = green
    if 'date' in todo.keys() and todo['date']:
        dt_obj = dtparser.parse(todo['date'])
        todo_str += " (Due: %s)" % pretty.date(dt_obj)
    for check in todo['checklist']:
        if not check['completed']:
            todo_str += "\n\t%s" % check['text']
        elif completed_faint:
            todo_str += faint("\n\t(-) %s" % check['text'])
    if notes and 'notes' in todo.keys() and todo['notes']:
        todo_str += "\n\n\t%s" % todo['notes'].replace("\n", "\n\t")
    todo_str = color(todo_str)
    return todo_str

def print_change(user, response):
    """Print the stat change expressed in the response."""
    old_exp = user['stats']['exp']
    old_hp = user['stats']['hp']
    old_gp = user['stats']['gp']
    old_lvl = user['stats']['lvl']

    new_exp = response['exp']
    new_hp = response['hp']
    new_gp = response['gp']
    new_lvl = response['lvl']

    fragments = []
    if new_lvl > old_lvl:
        fragments.append("LEVEL UP! Say hello to level %d" % new_lvl)
    if new_hp < old_hp:
        fragments.append("%0.1f HP!" % (new_hp - old_hp))
    if new_exp > old_exp:
        fragments.append("%d XP!" % (new_exp - old_exp))
    if new_gp > old_gp:
        fragments.append("%0.1f GP!" % (new_gp - old_gp))
    if 'drop' in response['_tmp'].keys():
        try:
            fragments.append("%s %s dropped!" %(response['_tmp']['drop']['key'], response['_tmp']['drop']['type'])
        except KeyError:
            print "Found the key error:", response['_tmp']['drop']
    print "\n".join(fragments)

def ls(raw=False, completed=False, date=False, *tags):
    """
    Print the incomplete tasks, optionally filtered and sorted by tag and date.
    """
    user = get_user()

    if user['cached']:
        print "Cached"

    todos = [t for t in user['todos'] if 'completed' in t.keys()]
    incomplete_todos = [t for t in todos if not t['completed']]

    if raw:
        for i in incomplete_todos:
            print i
        return

    def sort_key(todo):
        # Sort with the earliest date first, undated events at the end
        if 'date' in todo.keys():
            return todo['date']
        else:
            return datetime.datetime(9999,12,31).isoformat()

    if date:
        incomplete_todos.sort(key=sort_key)

    if tags:
        tagged_todos = defaultdict(list)
        for loop_todo in incomplete_todos:
            for tag in loop_todo['tags']:
                tagged_todos[tag].append(loop_todo)

        for tag in tags:
            print tag
            for loop_todo in tagged_todos[user['reverse_tag_dict'][tag]]:
                print "\t" + get_todo_str(user, loop_todo, completed_faint=completed).replace("\n", "\n\t")
            print ""

    else:
        for loop_todo in incomplete_todos:
            print get_todo_str(user, loop_todo, completed_faint=completed)

def stats():
    """Print the HP, MP, and XP bars, with some nice coloring."""
    user = get_user()

    current_hp = int(user['stats']['hp'])
    max_hp = int(user['stats']['maxHealth'])
    current_mp = int(user['stats']['mp'])
    max_mp = int(user['stats']['maxMP'])
    current_exp = int(user['stats']['exp'])
    level_exp = int(user['stats']['toNextLevel'])

    print_chr = "="
    width = 60

    hp_percent = min(float(current_hp) / max_hp, 1.0)
    mp_percent = min(float(current_mp) / max_mp, 1.0)
    xp_percent = min(float(current_exp) / level_exp, 1.0)

    if hp_percent < 0.25:
        hp_color = red
    elif hp_percent < 0.5:
        hp_color = yellow
    else:
        hp_color = green

    hp_bar = (print_chr*int(hp_percent*width)).ljust(width)
    mp_bar = (print_chr*int(mp_percent*width)).ljust(width)
    xp_bar = (print_chr*int(xp_percent*width)).ljust(width)

    print "HP: " + hp_color("[" + hp_bar + "]")
    print "MP: " + blue("[" + mp_bar + "]")
    print "XP: [" + xp_bar + "]"
    if user['cached']:
        print "(Cached)"

def add(todo, due="", *tags):
    """Add a todo with optional tags and due date in natural language."""
    api = get_api()
    user = get_user(api)

    added_tags = {}
    for tag in tags:
        tag_id = user['reverse_tag_dict'][tag.replace("+", "")]
        if tag_id:
            added_tags[tag_id] = True
        else:
            raise Exception("Tag %s not in %s" %(tag, str(user['reverse_tag_dict'].keys())))

    due_date = None
    # Process the input date string into a datetime
    if due:
        cal = Calendar()
        unaware_dt = cal.nlp(due)
        if not unaware_dt:
            raise Exception("Due date %s unclear" % due)
        else:
            code = unaware_dt[0][1]
            unaware_dt = unaware_dt[0][0]
            # If no time is supplied, assume 6pm
            if code == 1:
                unaware_dt = unaware_dt.replace(hour=18)
        if os.environ.get('HABIT_TZ'):
            localtz = pytz.timezone(os.environ.get('HABIT_TZ'))
        else:
            localtz = get_localzone()
        aware_dt = localtz.localize(unaware_dt)
        due_date = aware_dt.isoformat()

    api.create_task(api.TYPE_TODO, todo, date=due_date, tags=added_tags)

def detail(todo_string):
    user = get_user()
    todo = match_todo_by_string(user, todo_string)['todo']
    print get_todo_str(user, todo, notes=True)

def match_todo_by_string(user, todo_string, todos=None, match_checklist=False):
    """
    Returns the best match from all the user's incomplete tasks.

    The returned object is a dictionary with keys 'todo', 'parent' and
    'check_index'.  'parent' and 'check_index' are only used if the matched
    item is a checklist item, in which case they contain the parent todo and
    the index number of the checklist item.
    """
    if not todos:
        todos = [t for t in user['todos'] if 'completed' in t.keys()]

    incomplete_todos = []

    # Get all the incomplete todos and checklist items
    for todo in todos:
        if not todo['completed']:
            incomplete_todos.append({'todo':todo,
                                     'parent': None,
                                     'check_index': None})
            if 'checklist' in todo.keys():
                for j, item in enumerate(todo['checklist']):
                    if not item['completed']:
                        incomplete_todos.append({'todo':item,
                                                 'parent':todo,
                                                 'check_index':j})

    processor = lambda x: x['todo']['text']

    selected_todo = process.extractOne(todo_string,
                                       incomplete_todos,
                                       processor=processor)[0]

    return selected_todo


def addcheck(check, parent_str):
    """Add a checklist item to an existing todo matched by natural language."""
    api = get_api()
    user = get_user(api)
    selected_todo = match_todo_by_string(user, parent_str)

    if not selected_todo:
        print "No match found."
    else:
        parent = selected_todo['todo']
        print parent['text']
        if confirm(resp=True):
            if not 'checklist' in parent.keys():
                parent['checklist'] = []
            parent['checklist'].append({'text': check, 'completed': False})
            response = api.update_task(parent['id'], parent)
            print get_todo_str(user, response, completed_faint=True)


def do(*todos):
    """Complete a task, selected by natural language, with a confirmation."""
    todo_string = " ".join(todos)
    api = get_api()
    user = get_user(api)

    selected_todo = match_todo_by_string(user, todo_string, match_checklist=True)

    print selected_todo['todo']['text']
    if confirm(resp=True):
        # If it has a parent, it is a checklist item
        parent = selected_todo['parent']
        if parent:

            # Mark the checklist item as complete within the parent and repost
            check_index = selected_todo['check_index']
            parent['checklist'][check_index]['completed'] = True
            response = api.update_task(parent['id'], parent)
            # Print the remaining sections of the task
            print get_todo_str(user, response, completed_faint=True)

        # Otherwise it is a normal to-do
        else:
            response = api.perform_task(selected_todo['todo']['id'], api.DIRECTION_UP)
            print_change(user, response)

def main():
    argh_parser = argh.ArghParser()
    argh_parser.add_commands([ls, stats, add, addcheck, do, detail])
    argh_parser.dispatch()

if __name__ == "__main__":
    main()

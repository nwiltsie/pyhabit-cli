#!/usr/bin/env python
"""
A command line interface to HabitRPG.
"""

# Standard library imports
import datetime
import os
import pickle
import sys
import textwrap
from collections import defaultdict
from itertools import groupby

# Third party imports
import argh
import colors
import dateutil.parser
from argh.decorators import named
from tzlocal import get_localzone
from requests import ConnectionError
from fuzzywuzzy import process

# Same-project imports
import habitcli.pretty as pretty
from pyhabit import HabitAPI
from habitcli.utils import confirm, serialize_date, deserialize_date
from habitcli.utils import parse_datetime_from_date_str, read_config
from habitcli.utils import get_default_config_filename

CACHE_DIR = os.path.dirname(os.path.realpath(__file__))

CONFIG = read_config()


def get_api(user_id=None, api_key=None):
    """Get the HabitRPG api object."""
    if not user_id:
        user_id = CONFIG["user_id"]
    if not api_key:
        api_key = CONFIG["api_key"]
    return HabitAPI(user_id, api_key)


def save_user(user):
    """Save the user object to a file."""
    pickle.dump(user, open(os.path.join(CACHE_DIR, ".habit.p"), 'wb'))


def load_user():
    """Load the user object from the cache."""
    return pickle.load(open(os.path.join(CACHE_DIR, ".habit.p"), 'rb'))


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

    if 'err' in user.keys():
        print "Error '%s': Is the configuration in %s correct?" % \
            (user['err'], get_default_config_filename())
        sys.exit(1)

    # Add tag dictionaries to the user object
    tag_dict = defaultdict(lambda: "+missingtag")
    reverse_tag_dict = defaultdict(unicode)
    color_dict = defaultdict(lambda: lambda x: x)
    for tag in [tag for tag in user['tags'] if tag['name'] in CONFIG['tasks']]:
        tag_dict[tag['id']] = tag['name']
        reverse_tag_dict[tag['name']] = tag['id']

        if tag['name'] in CONFIG['taskcolors'].keys():
            if CONFIG['taskcolors'][tag['name']] in colors.COLORS:
                color = getattr(colors, CONFIG['taskcolors'][tag['name']])
                color_dict[tag['name']] = color
                color_dict[tag['id']] = color

    user['tag_dict'] = tag_dict
    user['reverse_tag_dict'] = reverse_tag_dict
    user['color_dict'] = color_dict
    return user


def get_planning_date(todo):
    """Extract the planning due date string from the task."""
    planned_date = deserialize_date(todo['notes'])

    if planned_date:
        return planned_date
    else:
        return None


def set_planning_date(api, todo, plan_date, submit=True):
    """
    Set the planning due date.
    Wipes out the current 'notes' field.
    Returns the updated todo.
    """
    todo['notes'] = serialize_date(plan_date)
    if submit:
        return api.update_task(todo['id'], todo)
    else:
        return todo


def has_tags(todo, tags):
    """Returns the subset of 'tags' that are applied to the todo."""
    return list(set(tags) & set(todo['tags'].keys()))


def get_todo_str(user, todo, date=False, completed_faint=False, notes=False):
    """Get a nicely formatted and colored string describing a task."""
    todo_str = "%-*s" % (40, todo['text'])

    # If dates should be printed, add the planning and drop-dead dates
    if date:
        plan_date = ""
        plan_date_obj = get_planning_date(todo)
        if plan_date_obj:
            plan_date = pretty.date(plan_date_obj)

        due = ""
        if 'date' in todo.keys() and todo['date']:
            dt_obj = dateutil.parser.parse(todo['date'])
            due = pretty.date(dt_obj)

        todo_str += " Plan: %-*s Due:%-*s" % (15, plan_date, 15, due)

    # Underline the string if the task is urgent
    tags = [tag for tag in todo['tags'].keys() if todo['tags'][tag]]
    if 'urgent' in [user['tag_dict'][tag] for tag in tags]:
        todo_str = colors.underline(todo_str)

    # Make the string faint if it has been completed
    if completed_faint:
        if 'completed' in todo.keys() and todo['completed']:
            todo_str = colors.faint(todo_str)

    # Format the notes as an indented block of text
    if notes:
        wrapper = textwrap.TextWrapper(initial_indent=" "*4,
                                       subsequent_indent=""*4)
        todo_str += "\n" + wrapper.fill(todo['notes'])

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
        drop_key = response['_tmp']['drop']['key']
        drop_type = response['_tmp']['drop']['type']
        fragments.append("%s %s dropped!" % (drop_key, drop_type))
    print "\n".join(fragments)


@named('ls')
def list_todos(raw=False, completed=False, list_tasks=False, *tags):
    """
    Print the incomplete tasks, optionally filtered and sorted by tag and date.
    """
    user = get_user()

    if user['cached']:
        print 'Cached'

    todos = [t for t in user['todos'] if 'completed' in t.keys()]

    if not completed:
        todos = [t for t in todos if not t['completed']]

    if tags:
        tag_ids = [user['reverse_tag_dict'][t.replace("+", "")] for t in tags]
        todos = [todo for todo in todos if has_tags(todo, tag_ids)]

    # Print the raw json data
    if raw:
        for todo in todos:
            print todo
        return

    if list_tasks:
        for task in CONFIG['tasks']:
            print user['color_dict'][task](task),
        else:
            print
            print

    def group_plan_date(todo):
        """
        Extract a pretty date, with all past dates listed 'OVERDUE'.
        """
        plan_date = get_planning_date(todo)
        if plan_date:
            if plan_date.date() < datetime.datetime.now().date():
                return "OVERDUE"
            else:
                return pretty.date(plan_date.date())
        else:
            return "Unplanned"

    todos = _nice_sort(todos, user)

    for plan_date, grouped_todos in groupby(todos, group_plan_date):
        print "%s:" % plan_date

        for tag, tagtodos in groupby(grouped_todos,
                                     lambda x: get_primary_tag(user, x)):
            color = user['color_dict'][tag]
            for todo in tagtodos:
                print "\t", color(get_todo_str(user, todo))


@named('stats')
def print_stat_bar():
    """Print the HP, MP, and XP bars, with some nice coloring."""
    user = get_user()

    current_hp = int(user['stats']['hp'])
    max_hp = int(user['stats']['maxHealth'])
    current_mp = int(user['stats']['mp'])
    max_mp = int(user['stats']['maxMP'])
    current_exp = int(user['stats']['exp'])
    level_exp = int(user['stats']['toNextLevel'])

    width = 60

    hp_percent = min(float(current_hp) / max_hp, 1.0)
    mp_percent = min(float(current_mp) / max_mp, 1.0)
    xp_percent = min(float(current_exp) / level_exp, 1.0)

    if hp_percent < 0.25:
        hp_color = colors.red
    elif hp_percent < 0.5:
        hp_color = colors.yellow
    else:
        hp_color = colors.green

    hp_bar = ("="*int(hp_percent*width)).ljust(width)
    mp_bar = ("="*int(mp_percent*width)).ljust(width)
    xp_bar = ("="*int(xp_percent*width)).ljust(width)

    print "HP: " + hp_color("[" + hp_bar + "]")
    print "MP: " + colors.blue("[" + mp_bar + "]")
    print "XP: [" + xp_bar + "]"
    if user['cached']:
        print "(Cached)"


@named('add')
def add_todo(todo, due_date="", plan_date="", *tags):
    """Add a todo with optional tags and due date in natural language."""
    api = get_api()
    user = get_user(api)

    added_tags = {}
    for tag in tags:
        if tag.replace("+", "") in user['reverse_tag_dict'].keys():
            tag_id = user['reverse_tag_dict'][tag.replace("+", "")]
            added_tags[tag_id] = True
        else:
            valid_tags = user['reverse_tag_dict'].keys()
            raise Exception("Tag %s not in %s" % (tag, str(valid_tags)))

    due_date_obj = None
    # Process the input date string into a datetime
    if due_date:
        due_date_obj = parse_datetime_from_date_str(due_date).isoformat()

    note = None
    if plan_date:
        plan_date_obj = parse_datetime_from_date_str(plan_date)
        note = set_planning_date(api, {'notes': ''},
                                 plan_date_obj, submit=False)['notes']

    api.create_task(api.TYPE_TODO, todo, date=due_date_obj,
                    tags=added_tags, notes=note)


@named('detail')
def print_detailed_string(todo_string):
    """Print a detailed description of the described todo."""
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
            incomplete_todos.append({'todo': todo,
                                     'parent': None,
                                     'check_index': None})
            if 'checklist' in todo.keys():
                for j, item in enumerate(todo['checklist']):
                    if not item['completed']:
                        incomplete_todos.append({'todo': item,
                                                 'parent': todo,
                                                 'check_index': j})

    processor = lambda x: x['todo']['text']

    selected_todo = process.extractOne(todo_string,
                                       incomplete_todos,
                                       processor=processor)[0]

    return selected_todo


def get_primary_tag(user, todo):
    """
    Get the primary tag of a todo. Each todo should have a single task tag,
    although it may have further decorative tags.
    """
    tag_strs = [user['tag_dict'][t]
                for t in todo['tags'].keys()
                if todo['tags'][t]]

    primary_tags = list(set(tag_strs) & set(CONFIG['tasks']))
    assert len(primary_tags) <= 1, "There should only be one primary tag"

    if primary_tags:
        return primary_tags[0]
    else:
        return None


@named('addcheck')
def add_checklist_item(check, parent_str):
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
            if 'checklist' not in parent.keys():
                parent['checklist'] = []
            parent['checklist'].append({'text': check, 'completed': False})
            response = api.update_task(parent['id'], parent)
            print get_todo_str(user, response, completed_faint=True)


@named('plan')
def update_todo_plan_date(todo, planned_date):
    """Set the planning date for a task, selected by natural language."""
    api = get_api()
    user = get_user(api)

    selected_todo = match_todo_by_string(user, todo)['todo']
    parsed_date = parse_datetime_from_date_str(planned_date)
    print "Change do-date of '%s' to %s?" % (selected_todo['text'],
                                             pretty.date(parsed_date))
    if confirm(resp=True):
        set_planning_date(api, selected_todo, parsed_date)


@named('delete')
def delete_todo(*todos):
    """Delete a task."""
    todo_string = " ".join(todos)
    api = get_api()
    user = get_user(api)

    selected_todo = match_todo_by_string(user, todo_string)['todo']
    print "Delete '%s'?" % selected_todo['text']
    if confirm(resp=True):
        api.delete_task(selected_todo['id'])


@named('do')
def complete_todo(*todos):
    """Complete a task, selected by natural language, with a confirmation."""
    todo_string = " ".join(todos)
    api = get_api()
    user = get_user(api)

    selected_todo = match_todo_by_string(user,
                                         todo_string,
                                         match_checklist=True)

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
            response = api.perform_task(selected_todo['todo']['id'],
                                        api.DIRECTION_UP)
            print_change(user, response)


def _nice_sort(todos, user=None):
    if not user:
        user = get_user()
    def sort_primary_tag(user, todo):
        """
        Return the list index in CONFIG['tasks'] of the primary todo tag.
        """
        tag = get_primary_tag(user, todo)
        if tag:
            return CONFIG['tasks'].index(tag)
        else:
            return 99999

    def sort_plan_key(todo):
        """
        Extract the planning date for sorting, or a dummy far-future date.
        """
        plan_date = get_planning_date(todo)
        if plan_date:
            return plan_date
        else:
            localtz = get_localzone()
            far_future_date = datetime.datetime(2999, 12, 31)
            return localtz.localize(far_future_date)

    # Sort tasks by the task tag
    todos.sort(key=lambda x: sort_primary_tag(user, x))
    # Sort tasks by the planned do-date
    todos.sort(key=sort_plan_key)

    return todos

def main():
    """Main entry point to the command line interface."""

    argh_parser = argh.ArghParser()
    argh_parser.add_commands([list_todos,
                              print_stat_bar,
                              add_todo,
                              add_checklist_item,
                              delete_todo,
                              complete_todo,
                              print_detailed_string,
                              update_todo_plan_date])
    argh_parser.dispatch()

if __name__ == "__main__":
    main()

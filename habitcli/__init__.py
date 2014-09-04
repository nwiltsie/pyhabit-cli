#!/usr/bin/env python
"""
A command line interface to HabitRPG.
"""

# Standard library imports
import collections
import datetime
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
import habitcli.gui
import habitcli.pretty as pretty
from pyhabit import HabitAPI
from habitcli.utils import confirm, serialize_date, deserialize_date
from habitcli.utils import parse_datetime, read_config
from habitcli.utils import get_default_config_filename, save_user, load_user


class NoSuchTagException(Exception):
    """Exception to designate missing tags."""
    def __init__(self, tag, valid_tags):
        Exception.__init__(self)
        self.tag = tag
        self.tag = valid_tags

    def __str__(self):
        return "Tag '%s' does not exist" % self.value


class MultipleTasksException(Exception):
    """Exception for when multiple primary tags are assigned to a todo."""
    def __init__(self, todo, *tags):
        Exception.__init__(self)
        self.todo = todo
        self.tags = tags

    def __str__(self):
        return "Todo '%s' has multiple tasks: %s" % \
            (self.todo['id'], self.tags)


class Todo(collections.MutableMapping):
    """A dictionary that applies an arbitrary key-altering
       function before accessing the keys"""

    def __init__(self, *args, **kwargs):
        self.hcli = kwargs.pop('hcli', None)
        self.store = dict(*args, **kwargs)
        if not 'tags' in self:
            self['tags'] = {}

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __str__(self):
        return "(Todo) ID:'%s' Text:'%s'" % \
            (self.get('id', None), self.get('text', ''))

    def get_planning_date(self):
        """Extract the planning due date string from the task."""
        planned_date = deserialize_date(self['notes'])

        if planned_date:
            return planned_date
        else:
            return None

    def set_planning_date(self, plan_date, update=False):
        """
        Set the planning due date.
        Wipes out the current 'notes' field.
        Returns the updated todo.
        """
        self['notes'] = serialize_date(plan_date)
        if update:
            self.update_db()

    def get_due_date(self):
        """Extract the due date from the task as a datetime."""
        if 'date' in self.keys() and self['date']:
            return dateutil.parser.parse(self['date'])
        elif 'dateCompleted' in self.keys() and self['dateCompleted']:
            return dateutil.parser.parse(self['dateCompleted'])
        else:
            return None

    def set_due_date(self, due_date, update=False):
        """Set the due date."""
        self['date'] = due_date.isoformat()
        if update:
            self.update_db()

    def has_tags(self, tags):
        """
        Returns the subset of 'tags' that are applied to the todo.

        Tags are specified by ID, not by nice string name.
        """
        return list(set(tags) & set(self['tags'].keys()))

    def _update(self, updated_self):
        """
        Used after interactions with the API to update the stored todo details.
        """
        self.clear()
        self.update(updated_self)

    def update_db(self):
        """
        Call the HabitRPG API to update self, then replace self with the
        returned values.
        """
        updated_self = self.hcli.api.update_task(self['id'], dict(self))
        self._update(updated_self)

    def complete(self):
        """
        Call the HabitRPG API to mark self as completed.
        """
        updated_self = self.hcli.api.perform_task(self['id'],
                                                  self.hcli.api.DIRECTION_UP)
        self._update(updated_self)

    def create(self):
        """
        Used once to create the task on the HabitRPG database.
        """
        self._update(self.hcli.api.create_todo(dict(self)))

    def delete(self):
        """
        Used to delete the task from the HabitRPG database.
        """
        self.hcli.api.delete_task(self['id'])


class HabitCLI(object):
    """A class incorporating everything necessary to interact with HabitRPG."""
    def __init__(self):
        """Initialize the CLI object."""
        self.config = read_config()
        self.api = self._get_api()
        self.user = self.get_user()

    def _get_api(self, user_id=None, api_key=None):
        """Get the HabitRPG api object."""
        if not user_id and not api_key:
            if hasattr(self, 'api') and self.api:
                return self.api
        if not user_id:
            user_id = self.config["user_id"]
        if not api_key:
            api_key = self.config["api_key"]
        self.api = HabitAPI(user_id, api_key)
        return self.api

    def get_user(self, refresh=False):
        """Get the user object from HabitRPG (if possible) or the cache."""
        if not refresh and hasattr(self, 'user') and self.user:
            return self.user
        else:
            try:
                self.user = self.api.user()
                save_user(self.user)
                self.user['cached'] = False
            except ConnectionError:
                self.user = load_user()
                self.user['cached'] = True

            if 'err' in self.user.keys():
                print "Error '%s': Is the configuration in %s correct?" % \
                    (self.user['err'], get_default_config_filename())
                sys.exit(1)

            # Replace user['todos'] with todo objects
            for index, todo in enumerate(self.user['todos']):
                self.user['todos'][index] = Todo(todo, hcli=self)

            # Add tag dictionaries to the user object
            tag_dict = defaultdict(lambda: "+missingtag")
            reverse_tag_dict = defaultdict(unicode)
            color_dict = defaultdict(lambda: lambda x: x)
            for tag in [tag for tag in self.user['tags']
                        if tag['name'] in self.config['tasks']]:
                tag_dict[tag['id']] = tag['name']
                reverse_tag_dict[tag['name']] = tag['id']

                if tag['name'] in self.config['taskcolors'].keys():
                    if self.config['taskcolors'][tag['name']] in colors.COLORS:
                        color = getattr(colors,
                                        self.config['taskcolors'][tag['name']])
                        color_dict[tag['name']] = color
                        color_dict[tag['id']] = color

            self.user['tag_dict'] = tag_dict
            self.user['reverse_tag_dict'] = reverse_tag_dict
            self.user['color_dict'] = color_dict
            return self.user

    def get_todo_str(self,
                     todo,
                     date=False,
                     completed_faint=False,
                     notes=False):
        """Get a nicely formatted and colored string describing a task."""
        todo_str = "%-*s" % (40, todo['text'])

        # If dates should be printed, add the planning and drop-dead dates
        if date:
            plan_date = ""
            plan_date_obj = todo.get_planning_date()
            if plan_date_obj:
                plan_date = pretty.date(plan_date_obj)

            due = ""
            if 'date' in todo.keys() and todo['date']:
                dt_obj = dateutil.parser.parse(todo['date'])
                due = pretty.date(dt_obj)

            todo_str += " Plan: %-*s Due:%-*s" % (15, plan_date, 15, due)

        # Underline the string if the task is urgent
        tags = [tag for tag in todo['tags'].keys() if todo['tags'][tag]]
        if 'urgent' in [self.user['tag_dict'][tag] for tag in tags]:
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

    def _print_change(self, response):
        """Print the stat change expressed in the response."""
        old_exp = self.user['stats']['exp']
        old_hp = self.user['stats']['hp']
        old_gp = self.user['stats']['gp']
        old_lvl = self.user['stats']['lvl']

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
    def list_todos(self, raw=False, completed=False, list_tasks=False, *tags):
        """
        Print the incomplete tasks.
        """
        if self.user['cached']:
            print 'Cached'

        todos = [t for t in self.user['todos']
                 if 'completed' in t.keys()
                 and (completed or not t['completed'])]

        if tags:
            tag_ids = [self.user['reverse_tag_dict'][t.replace("+", "")]
                       for t in tags]
            todos = [todo for todo in todos if todo.has_tags(tag_ids)]

        # Print the raw json data
        if raw:
            for todo in todos:
                print todo
            return

        if list_tasks:
            for task in self.config['tasks']:
                print self.user['color_dict'][task](task),
            print
            print

        def group_plan_date(todo):
            """
            Extract a pretty date, with all past dates listed 'OVERDUE'.
            """
            plan_date = todo.get_planning_date()
            if plan_date:
                if plan_date.date() < datetime.datetime.now().date():
                    return "OVERDUE"
                else:
                    return pretty.date(plan_date.date())
            else:
                return "Unplanned"

        todos = self.sort_nicely(todos)

        for plan_date, grouped_todos in groupby(todos, group_plan_date):
            print "%s:" % plan_date

            for tag, tagtodos in groupby(grouped_todos,
                                         self.get_primary_tag):
                color = self.user['color_dict'][tag]
                for todo in tagtodos:
                    print "\t", color(self.get_todo_str(todo))

    @named('stats')
    def print_stat_bar(self):
        """Print the HP, MP, and XP bars, with some nice coloring."""
        current_hp = int(self.user['stats']['hp'])
        max_hp = int(self.user['stats']['maxHealth'])
        current_mp = int(self.user['stats']['mp'])
        max_mp = int(self.user['stats']['maxMP'])
        current_exp = int(self.user['stats']['exp'])
        level_exp = int(self.user['stats']['toNextLevel'])

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
        if self.user['cached']:
            print "(Cached)"

    @named('add')
    def add_todo(self, todo, due_date="", plan_date="", *tags):
        """Add a todo with optional tags and due date in natural language."""

        new_todo = Todo(text=todo, hcli=self)

        for tag in tags:
            if tag.replace("+", "") in self.user['reverse_tag_dict'].keys():
                tag_id = self.user['reverse_tag_dict'][tag.replace("+", "")]
                new_todo['tags'][tag_id] = True
            else:
                valid_tags = self.user['reverse_tag_dict'].keys()
                raise NoSuchTagException(tag, valid_tags)

        if due_date:
            new_todo.set_due_date(parse_datetime(due_date))

        if plan_date:
            new_todo.set_planning_date(parse_datetime(plan_date))

        new_todo.create()

    @named('detail')
    def print_detailed_string(self, todo_string):
        """Print a detailed description of the described todo."""
        todo = self.match_todo_by_string(todo_string)['todo']
        print self.get_todo_str(todo, date=True, notes=True)

    def match_todo_by_string(self, todo_string):
        """
        Returns the best match from all the user's incomplete tasks.

        The returned object is a dictionary with keys 'todo', 'parent' and
        'check_index'.  'parent' and 'check_index' are only used if the matched
        item is a checklist item, in which case they contain the parent todo
        and the index number of the checklist item.
        """
        todos = [t for t in self.user['todos'] if 'completed' in t.keys()]

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

    def get_primary_tag(self, todo):
        """
        Get the primary tag of a todo. Each todo should have a single task tag,
        although it may have further decorative tags.
        """
        tag_strs = [self.user['tag_dict'][t]
                    for t in todo['tags'].keys()
                    if todo['tags'][t]]

        primary_tags = list(set(tag_strs) & set(self.config['tasks']))

        if len(primary_tags) > 1:
            raise MultipleTasksException(todo['id'], primary_tags)

        if primary_tags:
            return primary_tags[0]
        else:
            return None

    def set_primary_tag(self, todo, tag, update=False):
        """
        Set the primary tag of a todo. This will unset any other primary tags
        currently applied.

        Returns the updated task.
        """
        for task_id in [self.user['reverse_tag_dict'][t]
                        for t in self.config['tasks']]:
            if task_id in todo['tags'].keys() and todo['tags'][task_id]:
                todo['tags'][task_id] = False

        todo['tags'][self.user['reverse_tag_dict'][tag]] = True

        if update:
            self.update_todo(todo)

    @named('addcheck')
    def add_checklist_item(self, check, parent_str):
        """Add a checklist item to a todo matched by natural language."""
        selected_todo = self.match_todo_by_string(parent_str)

        if not selected_todo:
            print "No match found."
        else:
            parent = selected_todo['todo']
            print parent['text']
            if confirm(resp=True):
                if 'checklist' not in parent.keys():
                    parent['checklist'] = []
                parent['checklist'].append({'text': check, 'completed': False})
                parent.update_db()
                print self.get_todo_str(parent, completed_faint=True)

    @named('plan')
    def update_todo_plan_date(self, todo, planned_date):
        """Set the planning date for a task, selected by natural language."""
        selected_todo = self.match_todo_by_string(todo)['todo']
        parsed_date = parse_datetime(planned_date)
        print "Change do-date of '%s' to %s?" % (selected_todo['text'],
                                                 pretty.date(parsed_date))
        if confirm(resp=True):
            selected_todo.set_planning_date(parsed_date, update=True)

    @named('delete')
    def delete_todo(self, *todos):
        """Delete a task."""
        todo_string = " ".join(todos)

        selected_todo = self.match_todo_by_string(todo_string)['todo']
        print "Delete '%s'?" % selected_todo['text']
        if confirm(resp=True):
            selected_todo.delete()

    @named('do')
    def complete_todo(self, *todos):
        """Complete a task selected by natural language with a confirmation."""
        todo_string = " ".join(todos)

        selected_todo = self.match_todo_by_string(todo_string)

        print selected_todo['todo']['text']
        if confirm(resp=True):
            # If it has a parent, it is a checklist item
            parent = selected_todo['parent']
            if parent:

                # Mark the checklist item as complete and repost
                check_index = selected_todo['check_index']
                parent['checklist'][check_index]['completed'] = True
                parent.update_db()
                # Print the remaining sections of the task
                print self.get_todo_str(parent, completed_faint=True)

            # Otherwise it is a normal to-do
            else:
                selected_todo['todo'].complete()
                self._print_change(selected_todo['todo'])

    def sort_nicely(self, todos):
        """Sort the todos by date and task."""
        def sort_primary_tag(todo):
            """
            Return the list index in self.config['tasks'] of the primary tag.
            """
            tag = self.get_primary_tag(todo)
            if tag:
                return self.config['tasks'].index(tag)
            else:
                return 99999

        def sort_plan_key(todo):
            """
            Extract the planning date for sorting, or a dummy far-future date.
            """
            plan_date = todo.get_planning_date()
            if plan_date:
                return plan_date
            else:
                localtz = get_localzone()
                far_future_date = datetime.datetime(2999, 12, 31)
                return localtz.localize(far_future_date)

        def sort_due_key(todo):
            """
            Extract the due date for sorting, or a dummy far-future date.
            """
            due_date = todo.get_due_date()
            if due_date:
                return due_date
            else:
                localtz = get_localzone()
                far_future_date = datetime.datetime(2999, 12, 31)
                return localtz.localize(far_future_date)

        # Sort tasks by the task tag
        todos.sort(key=sort_due_key)
        todos.sort(key=sort_primary_tag)
        # Sort tasks by the planned do-date
        todos.sort(key=sort_plan_key)

        return todos

    @named('gui')
    def launch_graphical_window(self, *tags):
        """
        Launch a graphical window to edit the tasks, optionally limited to
        those defined by the given tags.
        """
        todos = [t for t in self.user['todos']
                 if 'completed' in t.keys() and not t['completed']]
        if tags:
            tag_ids = [self.user['reverse_tag_dict'][t.replace("+", "")]
                       for t in tags]
            todos = [todo for todo in todos if todo.has_tags(tag_ids)]

        todos = self.sort_nicely(todos)
        habitcli.gui.make_gui(self, todos)


def main():
    """Main entry point to the command line interface."""

    hcli = HabitCLI()

    argh_parser = argh.ArghParser()
    argh_parser.add_commands([hcli.list_todos,
                              hcli.print_stat_bar,
                              hcli.add_todo,
                              hcli.add_checklist_item,
                              hcli.delete_todo,
                              hcli.complete_todo,
                              hcli.print_detailed_string,
                              hcli.update_todo_plan_date,
                              hcli.launch_graphical_window])
    argh_parser.dispatch()

if __name__ == "__main__":
    main()

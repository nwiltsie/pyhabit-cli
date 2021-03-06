"""A GUI table-based todo editor for the HabitCLI interface."""
# Standard lib imports
import Tkinter as tk
import tkMessageBox
import ttk

# Same-project imports
import habitcli
import habitcli.utils as utils


class ValueStore(object):
    """A stupid value store that should be replaced."""
    pass


class SimpleTableInput(tk.Frame):
    """Table layout for the todo editor."""
    def __init__(self, parent, hcli, data):
        tk.Frame.__init__(self, parent)

        self.hcli = hcli
        self.data = data

        # Register a command to use for validation
        self.val_tag = (self.register(self._val_tag), '%P', '%W')
        self.val_date = (self.register(self._validate_date),
                         '%P',
                         '%V',
                         '%W',
                         '%v')
        self.ex_val = (self.register(self.example_validate),
                       '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

        # Create the table of widgets
        for row, datum in enumerate(self.data):
            label = self._add_label(datum, row)
            tag = self._add_tag_field(datum, row)
            plan = self._add_plan_field(datum, row)
            due = self._add_due_field(datum, row)
            self._add_btn(datum, row, label, tag, plan, due)

        # adjust column weights so they all expand equally
        for column in range(5):
            self.grid_columnconfigure(column, weight=1)
        # designate a final, empty row to fill up any extra space
        self.grid_rowconfigure(len(self.data), weight=1)

    def _add_label(self, datum, row):
        """Add a label for the given todo."""
        label = tk.Label(self, text=datum['text'])
        label.grid(row=row, column=0, sticky="w")
        return label

    def _add_tag_field(self, datum, row):
        """Add a primary tag field for the given todo."""
        tag = ttk.Combobox(self,
                           values=self.hcli.config['tasks']+[''],
                           validate='all',
                           validatecommand=self.val_tag)
        primary_tag = datum.get_primary_tag()
        tag.set(primary_tag if primary_tag else "")
        tag.original = primary_tag
        tag.grid(row=row, column=1, sticky="nsew")
        return tag

    def _add_plan_field(self, datum, row):
        """Add a plan date field for the given todo."""
        plan_date = datum.get_planning_date()
        plan_date_str = utils.format_date(plan_date)
        plan = tk.Entry(self, validate="all", validatecommand=self.val_date)
        plan.insert(0, plan_date_str)
        if utils.is_past(plan_date):
            plan['background'] = 'red'
        plan.original = plan_date
        plan.grid(row=row, column=2, sticky="nsew")
        return plan

    def _add_due_field(self, datum, row):
        """Add a due date field for the given todo."""
        due_date = datum.get_due_date()
        due_str = utils.format_date(due_date)
        due = tk.Entry(self, validate="all", validatecommand=self.val_date)
        due.insert(0, due_str)
        if utils.is_past(due_date):
            due['background'] = 'red'
        due.original = due_date
        due.grid(row=row, column=3, sticky="nsew")
        return due

    def _add_btn(self, datum, row, label, tag, plan, due):
        """Add update button for the given todo."""
        def btn_callback():
            """Update the associated todo with the changed fields."""
            fragments = []
            updates = {}

            date_fmt_str = "%s:\n\tFrom: %s\n\tTo:     %s"

            # Changes in planning date
            if plan.get():
                old_plan = datum.get_planning_date()
                new_plan = utils.parse_datetime(plan.get())
                if new_plan != old_plan:
                    fragments.append(date_fmt_str %
                                     ('Plan Date',
                                      utils.format_date(old_plan),
                                      utils.format_date(new_plan)))
                    updates['plan'] = new_plan

            # Changes in due date
            if due.get():
                old_due = datum.get_due_date()
                new_due = utils.parse_datetime(due.get())
                if new_due != old_due:
                    fragments.append(date_fmt_str %
                                     ('Due Date',
                                      utils.format_date(old_due),
                                      utils.format_date(new_due)))
                    updates['due'] = new_due

            # Changes in tag
            old_tag = datum.get_primary_tag()
            new_tag = tag.get()
            if new_tag != old_tag:
                fragments.append("Tag:\n\tFrom: %s\n\tTo: %s" %
                                 (old_tag, new_tag))
                updates['tag'] = new_tag

            if fragments:
                message = "\n".join(fragments)
                if tkMessageBox.askyesno("Update %s?" %
                                         datum['text'], message):

                    if 'tag' in updates:
                        datum.set_primary_tag(updates['tag'])
                    if 'plan' in updates:
                        datum.set_planning_date(updates['plan'])
                    if 'due' in updates:
                        datum.set_due_date(updates['due'])

                    datum.update_db()

                    tag.original = datum.get_primary_tag()
                    tag.original = tag.original if tag.original else ""
                    tag.set(tag.original)
                    self._val_tag(tag.get(), tag)

                    plan.delete(0, 1000)
                    plan.original = datum.get_planning_date()
                    plan.insert(0, utils.format_date(plan.original))
                    self._validate_date(plan.get(), 'focusout', plan, 'all')

                    due.delete(0, 1000)
                    due.original = datum.get_due_date()
                    due.insert(0, utils.format_date(due.original))
                    self._validate_date(due.get(), 'focusout', due, 'all')

                    print datum['text'], "updated!"

        btn = tk.Button(self,
                        text="Update",
                        takefocus=True,
                        highlightbackground="BLUE",
                        command=btn_callback)
        btn.grid(row=row, column=4, sticky="nsew")
        return btn

    def example_validate(self, d, i, P, s, S, v, V, W):
        """An example validation showing all the arguments."""
        print "OnValidate:"
        print "d='%s'" % d
        print "i='%s'" % i
        print "P='%s'" % P
        print "s='%s'" % s
        print "S='%s'" % S
        print "v='%s'" % v
        print "V='%s'" % V
        print "W='%s'" % W
        print
        return True

    def _val_tag(self, value, widget):
        """Validate the tag combobox to change the color."""
        if isinstance(widget, basestring):
            widget = self.nametowidget(widget)
        if hasattr(widget, 'original') and value != widget.original:
            # fixme: why doesn't this work?
            widget['background'] = 'green'
        else:
            widget['background'] = 'systemWindowBody'
        widget.after_idle(widget.config, {'validate': widget['validate']})

    def _validate_date(self, value, reason, widget, validation):
        """
        Validate that the date string can be parsed.

        Will clear the field if focus is lost and the date cannot be parsed,
        and enable the associated 'Update' button if it can.
        """
        if isinstance(widget, basestring):
            widget = self.nametowidget(widget)
        if reason in ['focusin', 'key']:
            return True
        elif reason == 'focusout':
            # Return True if the date parses
            try:
                new_dt = None
                if value:
                    new_dt = utils.parse_datetime(value)
                    widget.delete(0, 1000)
                    widget.insert(0, utils.format_date(new_dt))
                if new_dt != widget.original:
                    widget['background'] = 'green'
                elif new_dt and utils.is_past(new_dt):
                    widget['background'] = 'red'
                else:
                    widget['background'] = 'systemWindowBody'
                widget.after_idle(widget.config, {'validate': validation})
                return True
            except habitcli.utils.DateParseException:
                print "Invalid date entry,", value, ", deleting..."
                widget.delete(0, 1000)
                widget.after_idle(widget.config, {'validate': validation})
                return False
        # Return True for all other reasons
        else:
            return True


class TodoFrame(tk.Frame):
    """A tk Frame wrapper for the todos."""
    def __init__(self, parent, hcli, data):
        tk.Frame.__init__(self, parent)
        self.table = SimpleTableInput(self, hcli, data)
        self.table.pack(side="top", fill="both", expand=True)


def make_gui(hcli=None, todos=None):
    """Show a graphical window where the todos can be editted."""
    if not hcli:
        hcli = habitcli.HabitCLI()
    if not todos:
        user = hcli.get_user()
        todos = [t for t in user['todos'] if 'completed' in t.keys()]
        todos = [t for t in todos if not t['completed']]
        todos = hcli.sort_nicely(todos)

    root = tk.Tk()
    TodoFrame(root, hcli, todos).pack(side="top", fill="both", expand=True)
    root.mainloop()

if __name__ == '__main__':
    make_gui()

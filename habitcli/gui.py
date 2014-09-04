# Standard lib imports
import copy
import Tkinter as tk
import tkMessageBox
import ttk

# Same-project imports
import habitcli
from habitcli.utils import format_date, parse_datetime


class ValueStore(object):
    pass


class SimpleTableInput(tk.Frame):
    def __init__(self, parent, hcli, data):
        tk.Frame.__init__(self, parent)

        self.hcli = hcli
        self.data = data
        self.current_data = {}

        # Register a command to use for validation
        val_date = (self.register(self._validate_date), '%P', '%V', '%W', '%v')
        ex_val = (self.register(self.example_validate),
                  '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

        # Create the table of widgets
        for row, datum in enumerate(self.data):
            todo_id = datum['id']
            self.current_data[todo_id] = ValueStore()
            self.current_data[todo_id].old = datum

            # Label
            label = tk.Label(self, text=datum['text'])
            label.grid(row=row, column=0, sticky="w")
            self.current_data[todo_id].label = label

            # Primary tag combobox
            tag = ttk.Combobox(self,
                               values=self.hcli.config['tasks']+[''],
                               state='readonly')
            primary_tag = self.hcli.get_primary_tag(datum) or ""
            tag.set(primary_tag)
            tag.grid(row=row, column=1, sticky="nsew")
            tag.todo_id = todo_id
            self.current_data[todo_id].tag = tag

            # Planning date entry
            plan_date = self.hcli.get_planning_date(datum)
            plan_date_str = format_date(plan_date)
            plan = tk.Entry(self, validate="all", validatecommand=val_date)
            plan.insert(0, plan_date_str)
            plan.grid(row=row, column=2, sticky="nsew")
            plan.todo_id = todo_id
            self.current_data[todo_id].plan = plan

            # Due date entry
            due_date = hcli.get_due_date(datum)
            due_str = format_date(due_date)
            due = tk.Entry(self, validate="all", validatecommand=val_date)
            due.insert(0, due_str)
            due.grid(row=row, column=3, sticky="nsew")
            due.todo_id = todo_id
            self.current_data[todo_id].due = due

            # Update button
            def btn_callback_generator(todo_id):
                def btn_callback():
                    refs = self.current_data[todo_id]

                    new_tag = refs.tag.get()
                    fragments = []
                    new_todo = copy.deepcopy(refs.old)

                    date_fmt_str = "%s:\n\tFrom: %s\n\tTo:     %s"

                    # Changes in planning date
                    if refs.plan.get():
                        old_plan = self.hcli.get_planning_date(refs.old)
                        new_plan = parse_datetime(refs.plan.get())
                        if new_plan != old_plan:
                            fragments.append(date_fmt_str %
                                             ('Plan Date',
                                              format_date(old_plan),
                                              format_date(new_plan)))
                            self.hcli.set_planning_date(new_todo, new_plan)

                    # Changes in due date
                    if refs.due.get():
                        old_due = self.hcli.get_due_date(refs.old)
                        new_due = parse_datetime(refs.due.get())
                        if new_due != old_due:
                            fragments.append(date_fmt_str %
                                             ('Due Date',
                                              format_date(old_due),
                                              format_date(new_due)))
                            self.hcli.set_due_date(new_todo, new_due)

                    # Changes in tag
                    old_tag = self.hcli.get_primary_tag(refs.old)
                    if new_tag != old_tag:
                        fragments.append("Tag:\n\tFrom: %s\n\tTo: %s" %
                                         (old_tag, new_tag))
                        hcli.set_primary_tag(new_todo, new_tag)

                    if fragments:
                        message = "\n".join(fragments)
                        if tkMessageBox.askyesno("Update %s?" %
                                                 new_todo['text'], message):
                            print new_todo['text'], " updated!"

                            self.hcli.update_todo(new_todo)

                            # Disable everything
                            refs.label['state'] = 'disabled'
                            refs.tag['state'] = 'disabled'
                            refs.plan['state'] = 'disabled'
                            refs.due['state'] = 'disabled'
                            refs.btn['state'] = 'disabled'

                return btn_callback

            btn = tk.Button(self,
                            text="Update",
                            state='disabled',
                            takefocus=True,
                            highlightbackground="BLUE",
                            command=btn_callback_generator(datum['id']))
            btn.grid(row=row, column=4, sticky="nsew")
            btn.todo_id = todo_id
            self.current_data[todo_id].btn = btn

        # adjust column weights so they all expand equally
        for column in range(4):
            self.grid_columnconfigure(column, weight=1)
        # designate a final, empty row to fill up any extra space
        self.grid_rowconfigure(len(self.data), weight=1)

    def example_validate(self, d, i, P, s, S, v, V, W):
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

    def _validate_date(self, value, reason, widget, validation):
        widget = self.nametowidget(widget)
        if reason in ['focusin', 'key']:
            if hasattr(widget, 'todo_id'):
                self.current_data[widget.todo_id].btn['state'] = 'disabled'
            return True
        elif reason == 'focusout':
            # Return True if the date parses
            try:
                if value:
                    dt = parse_datetime(value)
                    widget.delete(0, 1000)
                    widget.insert(0,
                                  format_date(dt))
                self.current_data[widget.todo_id].btn['state'] = 'active'
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
    def __init__(self, parent, hcli, data):
        tk.Frame.__init__(self, parent)
        self.table = SimpleTableInput(self, hcli, data)
        self.table.pack(side="top", fill="both", expand=True)


if __name__ == '__main__':

    hcli = habitcli.HabitCLI()
    user = hcli.get_user()
    todos = [t for t in user['todos'] if 'completed' in t.keys()]
    todos = [t for t in todos if not t['completed']]
    todos = hcli._nice_sort(todos)

    root = tk.Tk()
    TodoFrame(root, hcli, todos).pack(side="top", fill="both", expand=True)
    root.mainloop()

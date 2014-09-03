import Tkinter as tk
import tkMessageBox
import ttk
import habitcli


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

            # Label
            label = tk.Label(self, text=datum['text'])
            label.grid(row=row, column=0, sticky="w")
            self.current_data[todo_id].label = label

            # Primary tag combobox
            tag = ttk.Combobox(self,
                               values=hcli.config['tasks']+[''],
                               state='readonly')
            primary_tag = hcli.get_primary_tag(datum) or ""
            tag.set(primary_tag)
            tag.grid(row=row, column=1, sticky="nsew")
            tag.todo_id = todo_id
            self.current_data[todo_id].tag = tag

            # Planning date entry
            plan_date = hcli.get_planning_date(datum)
            plan_date_str = habitcli.utils.make_unambiguous_date_str(plan_date)
            plan = tk.Entry(self, validate="all", validatecommand=val_date)
            plan.insert(0, plan_date_str)
            plan.grid(row=row, column=2, sticky="nsew")
            plan.todo_id = todo_id
            self.current_data[todo_id].plan = plan

            # Due date entry
            try:
                due_date = habitcli.utils.parse_datetime(datum['date'])
                due_str = habitcli.utils.make_unambiguous_date_str(due_date)
            except KeyError:
                due_str = ""
            due = tk.Entry(self, validate="all", validatecommand=val_date)
            due.insert(0, due_str)
            due.grid(row=row, column=3, sticky="nsew")
            due.todo_id = todo_id
            self.current_data[todo_id].due = due

            # Update button
            def btn_callback_generator(todo_id, tag, plan, due, old):
                def btn_callback():
                    new_plan_date = habitcli.utils.parse_datetime(plan.get())
                    new_due_date = habitcli.utils.parse_datetime(due.get())
                    new_tag = tag.get()
                    fragments = []
                    import copy
                    new_todo = copy.deepcopy(old)

                    if new_plan_date != hcli.get_planning_date(old):
                        fragments.append("Plan Date: From %s to %s" %
                                         (hcli.get_planning_date(old),
                                          new_plan_date))
                        hcli.set_planning_date(new_todo, new_plan_date)
                    if hasattr(old, 'date'):
                        old_due_date = hcli.parse_datetime(old['date'])
                    else:
                        old_due_date = None

                    if new_due_date != old_due_date:
                        fragments.append("Due Date: From %s to %s" %
                                         (old_due_date, new_due_date))
                        new_todo['date'] = new_due_date.isoformat()
                    old_tag = hcli.get_primary_tag(old)
                    if new_tag != old_tag:
                        fragments.append("Tag: From %s to %s" %
                                         (old_tag, new_tag))
                        print "fixme, tags not working"
                    if fragments:
                        message = "\n".join(fragments)
                        if tkMessageBox.askyesno("Update %s?", message):
                            print todo_id, " updated!"
                return btn_callback

            btn = tk.Button(self,
                            text="Update",
                            state='disabled',
                            takefocus=True,
                            highlightbackground="BLUE",
                            command=btn_callback_generator(datum['id'],
                                                           tag,
                                                           plan,
                                                           due,
                                                           datum))
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
                    dt = habitcli.utils.parse_datetime(value)
                    widget.delete(0, 1000)
                    widget.insert(0,
                                  habitcli.utils.make_unambiguous_date_str(dt))
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

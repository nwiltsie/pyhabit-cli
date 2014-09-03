import Tkinter as tk
import ttk
import habitcli

class SimpleTableInput(tk.Frame):
    def __init__(self, parent, data):
        tk.Frame.__init__(self, parent)

        self.data = data
        self._entry = {}

        # register a command to use for validation
        vcmd = (self.register(self._validate), "%P")
        val_date = (self.register(self._validate_date), "%P")
        vcmd2 = (self.register(self.OnValidate),
                '%d', '%i', '%P', '%s', '%S', '%v', '%V', '%W')

        user = habitcli.get_user()
        # create the table of widgets
        for row, datum in enumerate(self.data):
            label = tk.Label(self, text=datum['text'])
            label.grid(row=row, column=0, stick="nsew")
            self._entry[(row,0)] = label

            tag = ttk.Combobox(self, values=habitcli.CONFIG['tasks']+[''], state='readonly')
            primary_tag = habitcli.get_primary_tag(user, datum) or ""
            tag.set(primary_tag)
            tag.grid(row=row, column=1, stick="nsew")
            self._entry[(row,1)] = tag

            plan_date_str = habitcli.utils.make_unambiguous_date_str(habitcli.get_planning_date(datum))
            plan = tk.Entry(self, validate="key", validatecommand=vcmd)
            plan.insert(0, plan_date_str)
            plan.grid(row=row, column=2, stick="nsew")
            self._entry[(row,2)] = plan

            try:
                due_str = habitcli.utils.make_unambiguous_date_str(habitcli.parse_datetime_from_date_str(datum['date']))
            except KeyError:
                due_str = ""
            due = tk.Entry(self, validate="focusout", validatecommand=val_date)
            due.insert(0, due_str)
            due.grid(row=row, column=3, stick="nsew")
            self._entry[(row,3)] = due

            def btn_callback_generator(todo_id):
                def btn_callback():
                    print todo_id, " updated!"
                return btn_callback

            btn = tk.Button(self, text="Update", command=btn_callback_generator(datum['id']))
            btn.grid(row=row, column=4, stick="nsew")

        # adjust column weights so they all expand equally
        for column in range(4):
            self.grid_columnconfigure(column, weight=1)
        # designate a final, empty row to fill up any extra space
        self.grid_rowconfigure(len(self.data), weight=1)

    def get(self):
        '''Return a list of lists, containing the data in the table'''
        result = []
        for row in range(len(self.data)):
            current_row = []
            for column in range(4):
                index = (row, column)
                current_row.append(self._entry[index].get())
            result.append(current_row)
        return result

    def OnValidate(self, d, i, P, s, S, v, V, W):
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

    def _validate_date(self, P):
        if not P:
            return True
        try:
            dt = habitcli.parse_datetime_from_date_str(P)
            return True
        except habitcli.utils.DateParseException as e:
            return False

    def _validate(self, P):
        '''Perform input validation.
        '''
        return True

class Example(tk.Frame):
    def __init__(self, parent, data):
        tk.Frame.__init__(self, parent)
        self.table = SimpleTableInput(self, data)
        self.submit = tk.Button(self, text="Change task values", command=self.on_submit)
        self.table.pack(side="top", fill="both", expand=True)
        self.submit.pack(side="bottom")

    def on_submit(self):
        print(self.table.get())
        self.close()

import habitcli
user = habitcli.get_user()
todos = [t for t in user['todos'] if 'completed' in t.keys()]
todos = [t for t in todos if not t['completed']]

root = tk.Tk()
Example(root, todos).pack(side="top", fill="both", expand=True)
root.mainloop()

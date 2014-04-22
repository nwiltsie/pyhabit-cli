pyhabit
===============

HabitRPG python CLI (WIP)

Uses the env variables HABIT_USER_ID and HABIT_API_KEY for authentication

Installation
------------

Install using pip

    pip install git+git://github.com/nwiltsie/pyhabit
    pip install git+git://github.com/nwiltsie/pyhabit-cli

Requires
--------

* PyYAML
* pyhabit
* argh
* argcomplete
* parsedatetime
* python-dateutil
* tzlocal
* requests
* ansicolors
* fuzzywuzzy

Usage
-----

Set your env vars for the API

call it from command line using

    habit <method> <arg1> <arg2> <...>

List all your current to-dos:

    habit ls

List only tagged to-dos:

    Home:~ nwiltsie$ habit ls downhole
    downhole
        Add magnetometer reading code +downhole (Due: tomorrow)
        Update code to drive DROP by wire +downhole (Due: 3 days ago)

Add a new to-do with optional tags and natural language due date:

    habit add "Do the thing"
    habit add --due "Tomorrow" "Do that other thing" +15min

Complete a to-do with fuzzy string selection and HabitRPG stat change feedback:

    Home:~ nwiltsie$ habit do submit cli
    Submit CLI to GitHub
    Confirm [y]|n:
    10 XP!
    1.6 GP!
    Pink Cotton Candy dropped!

You can also complete checklist items:

    Home:~ nwiltsie$ habit ls cli
    cli
        Add checklist feature +cli
            Add ability to 'do' checklist item
            Add ability to 'add' checklist item

    Home:~ nwiltsie$ habit do do checklist item
    Add ability to 'do' checklist item
    Confirm [y]|n:
    Add checklist feature +cli
        (-) Add ability to 'do' checklist item
        Add ability to 'add' checklist item

Or add checklist items:

    Home:~ nwiltsie$ habit ls cli --completed
    cli
        Add checklist feature +cli
            (-) Add ability to 'do' checklist item
            Add ability to 'add' checklist item

    Home:~ nwiltsie$ habit addcheck "Test checklist feature" "checklist feature"
    Add checklist feature
    Confirm [y]|n:
    Add checklist feature +cli
        (-) Add ability to 'do' checklist item
        Add ability to 'add' checklist item
        Test checklist feature

Show stat bars (useful when paired with GeekTool):

    Home:~ nwiltsie$ habit stats
    HP: [============================================================]
    MP: [============================================================]
    XP: [===========                                                 ]

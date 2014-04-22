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

-037820:~ nwiltsie$ habit ls downhole
downhole
    Add magnetometer reading code +downhole (Due: tomorrow)
        Update code to drive DROP by wire +downhole (Due: 3 days ago)u

    Home:~ nwiltsie$ habit do submit cli
    Submit CLI to GitHub
    Confirm [y]|n: 
    10 XP!
    1.6 GP!
    Pink Cotton Candy dropped!

Show stat bars (useful when paired with GeekTool):

    Home:~ nwiltsie$ habit stats
    HP: [============================================================]
    MP: [============================================================]
    XP: [===========                                                 ]

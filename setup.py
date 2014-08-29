from setuptools import setup, find_packages

setup(
    name = "habitcli",
    description = "CLI to interact with HabitRPG",
    version = "0.3a",
    install_requires=[
        'distribute',
        'pyhabit',
        'argh',
        'argcomplete',
        'parsedatetime',
        'python-dateutil',
        'tzlocal',
        'requests',
        'ansicolors',
        'fuzzywuzzy',
        'pyyaml',
        'pytz',
    ],
    packages = find_packages(),
    author = "Nick Wiltsie",
    author_email = "nwiltsie@alum.mit.edu",
    license = "MIT",
    entry_points = {
        'console_scripts': [
            'habit = habitcli:main'
        ]
    },
    url = "http://github.com/nwiltsie/pyhabit-cli",
    download_url = "https://github.com/nwiltsie/pyhabit-cli/tarball/master"
)

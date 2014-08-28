from setuptools import setup, find_packages

setup(
    name = "pyhabit-cli",
    description = "CLI to interact with HabitRPG",
    version = "0.1a",
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
        'yaml',
    ],
    packages = find_packages(),
    author = "Nick Wiltsie",
    author_email = "nwiltsie@alum.mit.edu",
    license = "MIT",
    entry_points = {
        'console_scripts': [
            'habit = pyhabit_cli.cli:main'
        ]
    },
    url = "http://github.com/nwiltsie/pyhabit-cli",
    download_url = "https://github.com/nwiltsie/pyhabit-cli/tarball/master"
)

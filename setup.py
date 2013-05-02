from setuptools import setup, find_packages

setup(
    name = "pyhabit-cli",
    description = "CLI to interact with HabitRPG",
    version = "0.1a",
    install_requires=[
        'distribute',
        'pyhabit',
        'PyYAML'
    ],
    packages = find_packages(),
    author = "Xeross",
    author_email = "contact@xeross.me",
    license = "MIT",
    entry_points = {
        'console_scripts': [
            'habit = pyhabit_cli.cli:main'
        ]
    },
    url = "http://github.com/xeross/pyhabit-cli",
    download_url = "https://github.com/xeross/pyhabit-cli/tarball/master"
)

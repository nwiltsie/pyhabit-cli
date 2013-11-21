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
    author = "3onyc",
    author_email = "3onyc@x3tech.com",
    license = "MIT",
    entry_points = {
        'console_scripts': [
            'habit = pyhabit_cli.cli:main'
        ]
    },
    url = "http://github.com/3onyc/pyhabit-cli",
    download_url = "https://github.com/3onyc/pyhabit-cli/tarball/master"
)

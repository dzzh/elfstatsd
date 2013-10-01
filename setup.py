from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup
from setuptools.command.test import test as TestCommand
from setuptools.command.install import install as InstallCommand
from subprocess import call
import elfstatsd
import os

def read(file_name):
    return open(os.path.join(os.path.dirname(__file__), file_name)).read()

class PyTest(TestCommand):
    user_options = []
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        raise SystemExit(pytest.main(self.test_args))

class CustomInstall(InstallCommand):
    def run(self):
        # Call parent
        InstallCommand.run(self)
        # Execute commands
        call(['sh', 'scripts/post-install.sh'])

setup(
    name='elfstatsd',
    version=elfstatsd.__version__,
    description='A daemon application to aggregate data from httpd logs in ELF format for Munin',
    author='Zmicier Zaleznicenka',
    author_email='Zmicier.Zaleznicenka@gmail.com',
    license="MIT",
    keywords="munin apache tomcat nginx elf access log",
    url='https://github.com/dzzh/elfstatsd',
    cmdclass = {'test': PyTest, 'install': CustomInstall},
    packages=['elfstatsd'],
    install_requires=[
        'python-daemon>=1.6',
        'lockfile>=0.9',
        'apachelog>=1.1'
    ],
    tests_require=['pytest'],
    provides=['elfstatsd'],
    platforms=['Linux'],
    data_files = [
        ('/etc/init.d', ['scripts/elfstatsd']),
    ],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: No Input/Output (Daemon)",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 2 :: Only",
        "Topic :: Internet :: Log Analysis",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities"
    ],
)

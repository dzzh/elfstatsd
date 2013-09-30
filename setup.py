from setuptools import setup
from setuptools.command.test import test as TestCommand
import elfstatsd

class PyTest(TestCommand):
    user_options = []
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True
    def run_tests(self):
        import pytest
        raise SystemExit(pytest.main(self.test_args))

setup(
    name='elfstatsd',
    version=elfstatsd.__version__,
    description='A daemon application to aggregate data from httpd logs in ELF format for Munin',
    author='Zmicier Zaleznicenka',
    author_email='Zmicier.Zaleznicenka@gmail.com',
    url='https://github.com/dzzh/elfstatsd',
    cmdclass = {'test': PyTest},
    packages=['elfstatsd'],
    requires=['daemon(>=1.6)','lockfile(>=0.9)','apachelog(>=1.1)'],
    tests_require=['pytest'],
    provides=['elfstatsd'],
    platforms=['Linux'],
    data_files = [
        ('/etc/init.d', ['scripts/elfstatsd']),
    ]
)

from ez_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages
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
        # We don't want to run post-install here if we package the module with bdist_rpm, thus this check
        # to make sure we're not building an RPM (quite dirty, yes, but I didn't come to a better way)
        if not self.record == 'INSTALLED_FILES':
            call(['sh', 'scripts/post-install.sh'])

setup(
    name='elfstatsd',
    version=elfstatsd.__version__,
    description='A daemon application to aggregate data from httpd logs in ELF format for Munin',
    author='Zmicier Zaleznicenka',
    author_email='Zmicier.Zaleznicenka@gmail.com',
    license="MIT",
    keywords="munin apache tomcat nginx elf access log monitoring",
    url='https://github.com/dzzh/elfstatsd',
    cmdclass={'test': PyTest, 'install': CustomInstall},
    packages=find_packages(),
    install_requires=[
        'python-daemon>=1.6',
        'lockfile>=0.9',
        'apachelog>=1.1'
    ],
    tests_require=['pytest'],
    provides=['elfstatsd'],
    platforms=['POSIX'],
    data_files=[
        ('/etc/init.d', ['scripts/etc/init.d/elfstatsd']),
        ('/etc/sysconfig', ['scripts/etc/sysconfig/elfstatsd']),
    ],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 4 - Beta",
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

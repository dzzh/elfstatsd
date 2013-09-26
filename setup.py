from distutils.core import setup
import elfstatsd

setup(
    name='elfstatsd',
    version=elfstatsd.__version__,
    description='A daemon application to aggregate data from httpd logs in ELF format for Munin',
    author='Zmicier Zaleznicenka',
    author_email='Zmicier.Zaleznicenka@gmail.com',
    url='https://github.com/dzzh/elfstatsd',
    packages=['elfstatsd'],
    requires=['daemon(>=1.6)','lockfile(>=0.9)','apachelog(>=1.1)'],
    platforms=['Linux'],
    scripts = ['elfstatsd/elfstatsd.py'],
    data_files = [
        ('/etc/init.d', ['scripts/elfstatsd']),
    ]
)

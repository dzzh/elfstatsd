from distutils.core import setup
from  setuptools.command.install import install as _install

class install(_install):
    pass

setup(
    cmdclass={'install': install},
    name='munindaemon',
    version='1.0',
    description='A daemon application to aggregate data from Apache logs for Munin plugins',
    author='Zmicier Zaleznicenka',
    author_email='Zmicier.Zaleznicenka@tomtom.com',
    url='http://vos.intra.local/display/SS3/Monitoring+Apache+performance+at+Community+servers+with+Munin',
    packages=['munindaemon'],
    requires=['python-daemon>=1.6','lockfile>=0.9'],
    scripts=['munindaemon/munindaemon'],
    platforms=['Linux']
)

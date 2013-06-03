from distutils.core import setup
import munindaemon

setup(
    name='munindaemon',
    version=munindaemon.__version__,
    description='A daemon application to aggregate data from Apache logs for Munin plugins',
    author='Zmicier Zaleznicenka',
    author_email='Zmicier.Zaleznicenka@tomtom.com',
    url='http://vos.intra.local/display/SS3/Monitoring+Apache+performance+at+Community+servers+with+Munin',
    packages=['munindaemon'],
    requires=['daemon(>=1.6)','lockfile(>=0.9)','apachelog(>=1.0)'],
    platforms=['Linux'],
    scripts = ['munindaemon/munindaemon.py'],
    data_files = [
        ('/etc/init.d', ['scripts/munindaemon']),
    ]
)

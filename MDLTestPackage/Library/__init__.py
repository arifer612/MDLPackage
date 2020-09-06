import os
from configparser import ConfigParser
from . import general
from . import databaseScraper
from . import tvTokyo

confDir = os.path.abspath(os.path.join(os.path.realpath(__file__), '../..', '..', 'config.conf'))
if not os.path.exists(confDir):
    conf = ConfigParser()
    keyDir = os.path.expanduser('~/.MDL.conf')
    logDir = os.path.expanduser('~/Logs')

    if not os.path.exists(logDir):
        os.mkdir(logDir)
    conf['DIRECTORIES'] = {'key': keyDir, 'log': logDir}
    with open(confDir, 'w') as r:
        conf.write(r)
else:
    conf = ConfigParser()
    conf.read(confDir)
    keyDir = os.path.expanduser(conf['DIRECTORIES']['key']) if conf['DIRECTORIES']['key'] \
        else os.path.expanduser('~/.MDL.conf')
    logDir = os.path.expanduser(conf['DIRECTORIES']['log']) if conf['DIRECTORIES']['log'] \
        else os.path.expanduser('~/Logs')

if not os.path.exists(keyDir):
    keyConf = ConfigParser()
    keyConf['USER'] = {'username': '', 'password': ''}
    with open(keyDir, 'w') as r:
        keyConf.write(r)
    os.chmod(keyDir, 0o600)

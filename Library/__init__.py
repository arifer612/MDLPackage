import os
from configparser import ConfigParser

confDir = os.path.abspath(os.path.join(os.path.realpath(__file__), '..', '..', 'config.conf'))
conf = ConfigParser()
conf.read(confDir)

keyDir = os.path.expanduser(conf['DIRECTORIES']['key']) if conf['DIRECTORIES']['key'] else os.path.expanduser('~')
logDir = os.path.expanduser(conf['DIRECTORIES']['log']) if conf['DIRECTORIES']['log'] else os.path.expanduser('~')

from . import general
from . import kakaku
from . import library
from . import tvTokyo

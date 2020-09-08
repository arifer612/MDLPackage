import os
from configparser import ConfigParser
import shutil


class Config:
    def __init__(self):
        self.dir = os.path.abspath(os.path.join(os.path.realpath(__file__), '../..', 'MDLConfig.conf'))
        self.conf = self.__keyDir = self._logDir = ''
        self.start()

    def start(self):
        if not os.path.exists(self.dir):
            self.conf = ConfigParser()
            self.__keyDir = os.path.expanduser('~/.keys/.MDL')
            self._logDir = os.path.expanduser('~/Documents/Logs')

            self.conf['DIRECTORIES'] = {'key': self.__keyDir, 'log': self._logDir}
            with open(self.dir, 'w') as r:
                self.conf.write(r)
        else:
            self.conf = ConfigParser()
            self.conf.read(self.dir)
            self.__keyDir = os.path.expanduser(self.conf['DIRECTORIES']['key']) if self.conf['DIRECTORIES']['key'] \
                else os.path.expanduser('~/.MDL.conf')
            self._logDir = os.path.expanduser(self.conf['DIRECTORIES']['log']) if self.conf['DIRECTORIES']['log'] \
                else os.path.expanduser('~/Logs')

        if not os.path.exists(os.path.split(self.__keyDir)[0]):
            os.makedirs(os.path.split(self.__keyDir)[0], exist_ok=True)
        if not os.path.exists(self._logDir):
            os.makedirs(self._logDir, exist_ok=True)
        if not os.path.exists(self.__keyDir):
            keyConf = ConfigParser()
            keyConf['USER'] = {'username': '', 'password': '', 'youtubeAPI': ''}
            with open(self.__keyDir, 'w') as r:
                keyConf.write(r)
            os.chmod(self.__keyDir, 0o600)

    def move(self, keydir='', logdir=''):
        if not (keydir or logdir):
            return
        else:
            if keydir:
                if not os.path.exists(os.path.split(keydir)[0]):
                    os.makedirs(os.path.split(keydir)[0], exist_ok=True)
                shutil.move(self.__keyDir, keydir)
                self.__keyDir = keydir
                print(f'Moved key file to {self.__keyDir}')
            if logdir:
                if not os.path.exists(logdir):
                    os.makedirs(logdir)
                shutil.move(self._logDir, logdir)
                self._logDir = logdir
                print(f'Relocated log directory to {self._logDir}')
            self.updateConf()

    def updateConf(self):
        with open(self.dir, 'w') as f:
            self.conf.write(f)


configFile = Config()

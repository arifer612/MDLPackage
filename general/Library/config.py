import os
from configparser import ConfigParser
import shutil
from distutils.util import strtobool
from getpass import getpass
from shutil import Error


def copytree(src, dst, symlinks=False):  # Obtained from shutil
    names = os.listdir(src)
    os.makedirs(dst, exist_ok=True)  # Added exist_ok=True
    errors = []
    for name in names:
        srcName = os.path.join(src, name)
        dstName = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcName):
                linkTo = os.readlink(srcName)
                os.symlink(linkTo, dstName)
            elif os.path.isdir(srcName):
                copytree(srcName, dstName, symlinks)
            else:
                shutil.copy2(srcName, dstName)
        except OSError as why:
            errors.append((srcName, dstName, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except Error as err:
            errors.extend(err.args[0])

    try:
        shutil.copystat(src, dst)
    except OSError as why:
        # can't copy file access times on Windows
        if why.winerror is None:
            errors.extend((src, dst, str(why)))
    if errors:
        raise Error(errors)


class Config:
    def __init__(self):
        self.dir = os.path.abspath(os.path.join(os.path.realpath(__file__), '../..', 'MDLConfig.conf'))
        self.conf = ConfigParser()
        self.version = self.__keyDir = self.logDir = None
        self.start()
        self.updateConf()

    def start(self):
        self.conf = ConfigParser()
        self.conf.read(self.dir)
        self.__keyDir = os.path.expanduser(self.conf['DIRECTORIES']['key']) if self.conf['DIRECTORIES']['key'] \
            else os.path.expanduser('~/.MDL.conf')
        self.logDir = os.path.expanduser(self.conf['DIRECTORIES']['log']) if self.conf['DIRECTORIES']['log'] \
            else os.path.expanduser('~/Documents/Logs')
        self.version = self.conf['PACKAGE']['version']

        if not os.path.exists(os.path.split(self.__keyDir)[0]):
            os.makedirs(os.path.split(self.__keyDir)[0], exist_ok=True)
        if not os.path.exists(self.logDir):
            os.makedirs(self.logDir, exist_ok=True)
        if not os.path.exists(self.__keyDir):
            keyConf = ConfigParser()
            keyConf['USER'] = {'username': '', 'password': '', 'youtubeAPI': ''}
            with open(self.__keyDir, 'w') as r:
                keyConf.write(r)
            os.chmod(self.__keyDir, 0o600)

    def updateConf(self):
        self.conf['DIRECTORIES'] = {
            'key': self.__keyDir.replace(os.path.expanduser('~/'), '~' + os.sep),  # For cleaner look on Linux
            'log': self.logDir.replace(os.path.expanduser('~/'), '~' + os.sep)   # For cleaner look on Linux
        }
        with open(self.dir, 'w') as r:
            self.conf.write(r)
        with open(self.dir, 'w') as f:
            self.conf.write(f)

    def move(self, key='', log=''):
        if not (key or log):
            return
        else:
            if key:
                key = os.path.abspath(os.path.expanduser(key))
                if key != self.__keyDir:
                    if not os.path.exists(os.path.split(key)[0]):
                        os.makedirs(os.path.split(key)[0], exist_ok=True)
                    shutil.move(self.__keyDir, key)
                    self.__keyDir = key
                    print(f'Moved key file to {self.__keyDir}')
                else:
                    pass
            if log:
                log = os.path.abspath(os.path.expanduser(log))
                if log != self.logDir:
                    if os.path.exists(log):
                        copytree(self.logDir, log, symlinks=False)
                    else:
                        shutil.move(self.logDir, log)
                    self.logDir = log
                    print(f'Relocated log directory to {self.logDir}')
                else:
                    pass
            self.updateConf()

    def newKeys(self, username=None, password=None, echo=True):
        if not (username and password):
            if echo:
                try:
                    echo = strtobool(input('Echo password? (y/n)'))
                except ValueError:
                    print('Invalid answer. Password will not be echoed.')
                    echo = False
            username = input('Username >>>')
            password = input('Password >>>') if echo else getpass('Password >>>')
        else:
            pass
        keyConf = ConfigParser()
        keyConf.read(self.__keyDir)
        keyConf['USER']['username'], keyConf['USER']['password'] = username, password
        with open(self.__keyDir) as f:
            keyConf.write(f)

    def print(self):
        print(
            f"----------------------------------------------------------------------------\n"
            f"                            MDLPackage v{self.version}\n"
            f"                          Configuration Settings\n\n"
            f"Key file\t\t@\t{self.__keyDir}\n"
            f"Log directory\t\t@\t{self.logDir}\n\n\n"
            f"                                Documentation\n\n"
            f"configFile.move(key=keyDir, log=logDir)\n\n"
            f"\tMoves key file or log directory to specified directory\n\n"
            f"configFile.newKeys(username=username, password=password, echo=bool)\n\n"
            f"\tWrites new login details into the key file without manually opening\n"
            f"\tthe file.\n"
            f"\tUsername and password have to passed as strings if declared.\n"
            f"\techo=True echoes the password as you input it;\n"
            f"\techo=False mutes the password as you input it.\n"
            f"\tWithout arguments, you will be prompted to input your login details.\n"
            f"----------------------------------------------------------------------------"
        )


configFile = Config()

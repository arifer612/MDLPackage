import json
import os
import urllib.error
import urllib.request

try:
    import cPickle as pickle
except ImportError:
    import pickle

import yaml
import requests
from bs4 import BeautifulSoup as bs


def saveImage(imageLink, rootDir, fileName=False, attempts=3):
    fileName = imageLink.split('/')[-1].replace('-', '_') if not fileName else fileName
    attempt = 0
    while attempt < attempts:
        try:
            urllib.request.urlretrieve(imageLink, os.path.join(rootDir, fileName))
            return fileName
        except urllib.error.HTTPError:
            attempt += 1
    return False


def revDict(dic):
    return dict(reversed(list(dic.items())))


def episodesAnalyse(castDict):
    for cast, episodeList in castDict.items():
        end = -1
        final = []
        for episode in episodeList:
            if episode > end + 1:
                final.append(str(episode))
            else:
                final[-1] = final[-1].split('-')[0] + f'-{episode}'
            end = episode
        castDict[cast] = f"(Ep {', '.join([episodeBunch for episodeBunch in final])})"
    return castDict


def soup(link, params=None, headers=None, cookies=None, data=None, post=False, JSON=False, response=False, delete=False,
         timeout=5, attempts=5, **kwargs):
    attempt = 0
    while attempt < attempts:
        try:
            if delete:
                request = requests.delete(link, params=params, headers=headers, data=data, timeout=timeout, **kwargs)
                return request.status_code == 200

            if not post:
                request = requests.get(link, params=params, headers=headers, cookies=cookies, data=data,
                                       timeout=timeout, **kwargs)
            elif int(post) == 1:
                request = requests.post(link, params=params, headers=headers, cookies=cookies, data=data,
                                        timeout=timeout, **kwargs)
            elif int(post) == -1:
                request = requests.patch(link, params=params, headers=headers, cookies=cookies, data=data,
                                         timeout=timeout, **kwargs)
            else:
                raise ValueError

            if not JSON and not response:
                return bs(request.content, 'lxml')
            elif JSON:
                return json.loads(request.content)
            elif response:
                return request
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            attempt += 1
    raise ConnectionRefusedError


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=80, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def loadLog(fileName, rootDir='.', flip=False):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        return {}
    else:
        with open(file, 'rb') as p:
            return pickle.load(p) if not flip else revDict(pickle.load(p))


def saveLog(data, fileName, rootDir='.', flip=False):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    with open(file, 'wb') as p:
        pickle.dump(data if not flip else revDict(data), p, protocol=pickle.HIGHEST_PROTOCOL)


class Log:
    def __init__(self, key, data):
        self.__key, self.data, self._counter = key, data, 0
        self._type = type(self.data)
        if self._type not in (dict, list, str):
            raise TypeError('Data can only be <dict>, <list>, or <str>')

    def __repr__(self):
        return f"{self.data}"

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        if self.data or self._type is not str:
            return self
        else:
            raise TypeError('self.__name__' is not iterable)

    def __next__(self):
        if self._counter == len(self):
            self._counter = 0
            raise StopIteration()

        if self._type is dict:
            key = list(self.data)[self._counter]
            result = (key, self.data[key])
        elif self._type is list:
            result = self.data[self._counter]

        self._counter += 1
        return result

    def add(self, data, force=False):
        if self._type is dict:
            if type(data) is not dict:
                raise TypeError('Data has to be a dictionary')
            if force:  # Overwrites data
                self.data = data
            else:  # Updates dictionary value
                self.data.update(data)

        elif self._type is list:
            if type(data) is not list:
                data = [data]
            if force:  # Overwrites data
                self.data = data
            else:  # Appends to end of list
                self.data += data

        elif self._type is str:
            if type(data) is not str:
                raise TypeError('Data has to be a string')
            self.data = data

    def remove(self, key=None):
        if type(key) is not list:
            key = [key]

        if self._type is dict and any(key):
            [self.data.pop(i, None) for i in key]

        elif self._type is list and data:
            [self.data.remove(i) for i in key if i in self.data]

        elif self._type is str:
            self.data = ""


def safeLoad(function):
    def runFunction(self, *args, **kwargs):
        self._load()
        result = function(self, *args, **kwargs)
        self._update()
        return result
    return runFunction


class ShowLog(Log):
    def __init__(self, fileName, rootDir='.', flip=False):
        self._fileName, self._rootDir, self._flip = fileName, rootDir, flip
        self._load()
        super().__init__(fileName, self.data)

    def __call__(self, *keys):
        if not keys:
            return {key: self(key).data if type(self(key)) is Log else self(key)
                for key in list(self.data)} if self.data else {}
        elif len(keys) == 1:
            return self.data[keys[0]]
        else:
            return "Only 1 key can be called"

    def _load(self):
        self.data = loadLog(self._fileName, self._rootDir, self._flip)

    def _update(self):
        saveLog(self.data, self._fileName, self._rootDir, self._flip)

    @safeLoad
    def add(self, key, data=None, force=False):
        if type(key) is dict:
            for i, j in key.items():
                if i in self.data:
                    self(i).add(j, force)
                else:
                    super().add({i: Log(i, j)})
        elif type(key) in (int, str):
            if key in self.data:
                self(key).add(data, force)
            else:
                super().add({key: Log(key, data)})
        else:
            raise TypeError("Data must be <dict>, <list>, or <str>")

    @safeLoad
    def remove(self, logKey, keys=None):  # use keys to pick and remove dictionary entries from logs
        if not keys:
            super().remove(logKey)
        else:
            if type(logKey) is not list:
                logKey = [logKey]
            [self(i).remove(keys) for i in logKey]

    @safeLoad
    def removeAll(self):
        if self.data:
            self.remove(list(self.data))


def readableLog(fileName, rootDir='.'):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        raise FileNotFoundError
    else:
        data = ShowLog(fileName, rootDir)
        file = os.path.splitext(file)[0] + '.yaml'
        with open(file, 'w') as j:
            yaml.safe_dump(data(), j, allow_unicode=True)
        return f"{file}"


def machinableLog(fileName, rootDir='.'):
    fileName = os.path.splitext(fileName)[0] + '.yaml'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        raise FileNotFoundError
    else:
        with open(file, 'r') as j:
            data = yaml.safe_load(j)
        dataLog = ShowLog(fileName, rootDir)
        dataLog.removeAll()
        dataLog.add(data)


def logConvert(fileName, rootDir='.', flip=False):
    data = loadLog(fileName, rootDir)
    dataLog = ShowLog(fileName, rootDir, flip)
    dataLog.removeAll()
    dataLog.add(data)

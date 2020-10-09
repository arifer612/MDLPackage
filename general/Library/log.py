import os
import pickle
import yaml
from .library import revDict


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


def safeLoad(function):
    def runFunction(self, *args, **kwargs):
        self._load()
        result = function(self, *args, **kwargs)
        self._update()
        return result
    return runFunction


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
            raise TypeError(f'{self.__name__} is not iterable')

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

        elif self._type is list and any(key):
            [self.data.remove(i) for i in key if i in self.data]

        elif self._type is str:
            self.data = ""


class LogFile(Log):
    def __init__(self, fileName, rootDir='.', flip=False):
        self._fileName, self._rootDir, self._flip = fileName, rootDir, flip
        self._load()
        super().__init__(fileName, self.data)
        self._update()  # Creates the file

    def keys(self):
        return list(self.data)

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


def readableLog(fileName, rootDir='.', quiet=False):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        raise FileNotFoundError
    else:
        data = LogFile(fileName, rootDir)
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
        dataLog = LogFile(fileName, rootDir)
        dataLog.removeAll()
        dataLog.add(data)

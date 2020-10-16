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

    def __call__(self, *keys):
        if not keys:
            return self.data
        else:
            try:
                if self._type is dict:
                    if keys[0] in list(self.data.keys()):
                        return self.data[keys[0]]
                    else:
                        raise LookupError

                elif self._type is list:
                    if keys[0] in len(self):
                        return self.data[keys[0]]
                    else:
                        raise LookupError

                elif self._type is str:
                    return self.data
            except LookupError:
                return KeyError if len(keys) == 1 else TypeError('list cannot be called')

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

    @staticmethod
    def _recursiveUpdate(data, newData):
        for i, j in newData.items():
            if i not in data:
                data.update({i: j})
            else:
                if type(data[i]) is dict and type(j) is dict:
                    self._recursiveUpdate(data[i], j)
                else:
                    if type(data[i]) is list and type(j) is not list:
                        j = [j]
                    try:
                        data[i] += j
                    except Exception as err:
                        print(f"Failed to update {i} because {err}")

    def add(self, data, force=False, string=False):
        if self._type is dict:
            if type(data) is not dict:
                raise TypeError('Data has to be a dictionary')
            if force:  # Overwrites data
                self.data = data
            else:  # Updates dictionary value
                self._recursiveUpdate(self.data, data)

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

    def __add__(self, other):
        if type(other) is not type(self):
            raise TypeError(f"{type(self)} can only concatenate with another {type(self)}")
        if self.__key != other.__key or self._type != other._type:
            raise NameError('Only equivalent Logs can be concatenated')
        temp_self = Log(self.__key, self())
        temp_self.add(other())
        return temp_self()

    def __radd__(self, other):
        self.add(self + other, force=True)


class LogFile(Log):
    def __init__(self, fileName, rootDir='.', flip=False):
        self._fileName, self._rootDir, self._flip = fileName, rootDir, flip
        self._load()
        super().__init__(fileName, self.data)
        self._update()  # Creates the file

    def __call__(self, *keys):
        if keys:
            return super().__call__(*keys).data
        else:
            data = super().__call__()
            for i, j in data.items():
                if type(j) in (Log, LogFile):
                    data[i] = j()
            return data

    def keys(self):
        return list(self.data.keys())

    def values(self):
        return list(self.data.values())

    def _load(self):
        self.data = loadLog(self._fileName, self._rootDir, self._flip)

    def _update(self):
        saveLog(self.data, self._fileName, self._rootDir, self._flip)

    @safeLoad
    def add(self, key, data=None, force=False, string=False):
        if type(key) is dict:
            for i, j in key.items():
                if i in self.data:
                    self.data[i].add(j, force)
                else:
                    super().add({i: Log(i, j)})
        elif type(key) in (int, str):
            if key in self.data:
                self.data[key].add(data, force)
            else:
                if string:
                    super().add({key: Log(key, str(data))}, force)
                else:
                    if type(data) not in (list, dict):
                        data = [data]
                    super().add({key: Log(key, data)}, force)
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
        raise FileNotFoundError(f"{fileName} does not exist")
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
        raise FileNotFoundError(f"{fileName} does not exist")
    else:
        with open(file, 'r') as j:
            data = yaml.safe_load(j)
        dataLog = LogFile(fileName, rootDir)
        dataOld = LogFile()
        try:
            dataLog.removeAll()
            dataLog.add(data)
        except Exception as err:
            print(f'ERROR: {err}')
            dataLog.add(dataOld)


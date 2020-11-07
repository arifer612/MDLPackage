import os
import pickle
import sys
from os.path import exists, abspath, expanduser, join, splitext
from typing import Dict, List, Union, Any

import yaml

from .library import revDict


def safeLoad(function):
    def runFunction(self, *args, **kwargs):
        self._load()
        result = function(self, *args, **kwargs)
        self._update()
        return result

    return runFunction


class Log:
    def __init__(self, key: Union[str, int], data: Union[dict, list, int, float, str]):
        self.__key, self.data, self._counter = key, data, 0
        if not isinstance(self.data, (dict, list, int, float, str)):
            raise TypeError(f"{type(self.data)} is not a supported data type.")

    def __repr__(self):
        return f"{self.data}"

    def __len__(self):
        return len(self.data)

    def __call__(self, *keys) -> Union[dict, list, str, int, float, "Log"]:
        if not keys:
            return self.data
        else:
            try:
                if isinstance(self.data, dict):
                    if keys[0] in list(self.data.keys()):
                        return self.data[keys[0]]
                    else:
                        raise LookupError

                elif isinstance(self.data, list):
                    if keys[0] in range(len(self)):
                        return self.data[keys[0]]
                    else:
                        raise LookupError

                elif isinstance(self.data, str):
                    return self.data

                else:
                    raise TypeError
            except LookupError:
                if len(keys) == 1:
                    raise KeyError
                raise TypeError("List cannot be called")
            except TypeError:
                raise TypeError(f"{type(self.data)} is not a supported type")

    def __iter__(self):
        if self.data or isinstance(self.data, (dict, list)):
            return self
        else:
            raise TypeError(f'{self.__name__} is not iterable')

    def __next__(self):
        if self._counter == len(self):
            self._counter = 0
            raise StopIteration()

        if isinstance(self.data, dict):
            key = list(self.data)[self._counter]
            result = (key, self.data[key])
        elif isinstance(self.data, list):
            result = self.data[self._counter]
        else:
            raise TypeError

        self._counter += 1
        return result

    def _recursiveUpdate(self, data: Dict[Union[str, int], Any],
                         newData: Dict[Union[str, int], Any]) -> None:
        for i, j in newData.items():
            if i not in data.keys():
                data.update({i: j})
            else:
                if isinstance(data[i], dict) and isinstance(j, dict):  # Repeats update
                    self._recursiveUpdate(data[i], j)
                elif isinstance(data[i], list):
                    if not isinstance(j, list):
                        j = [j]
                    try:
                        data[i].extend(j)
                    except Exception as err:
                        print(f"Failed to update {i} because {err}")
                elif isinstance(data[i], (int, float)) and isinstance(j, (int, float)):  # Adds the values
                    data[i] += j
                else:  # Replaces the value
                    data[i] = j

    def add(self, data: Union[dict, list, str, int, float], force: bool = False, string: bool = False) -> None:
        if force:
            self.data = data

        if isinstance(self.data, dict):
            if not isinstance(data, dict):
                raise TypeError('Data has to be a dictionary')
            else:  # Updates dictionary value
                self._recursiveUpdate(self.data, data)
        elif isinstance(self.data, list):
            if not isinstance(data, list):
                data = [data]
            self.data.extend(data)
        elif isinstance(self.data, str):
            if type(data) is not str:
                raise TypeError('Data has to be a string')
            self.data = data
        elif isinstance(self.data, (int, float)):
            if not isinstance(data, (int, float)):
                raise TypeError("Data has to be an integer or float")
            self.data += data

    def remove(self, key: Union[List[Union[str, int]], str, int] = None) -> None:
        if not isinstance(key, list):
            key = [key]

        if isinstance(self.data, dict):
            [self.data.pop(i, None) for i in key]
        elif isinstance(self.data, list):
            [self.data.remove(i) for i in key if i in self.data]
        elif isinstance(self.data, str):
            self.data = ""
        elif isinstance(self.data, (int, float)):
            self.data = 0

    def __add__(self, other) -> dict:
        if not isinstance(other, Log):
            raise TypeError(f"Cannot concatenate a {type(other)} with a Log")
        if isinstance(self.data, type(other.data)) and \
                not all([isinstance(self.data, (int, float)), isinstance(self.data, (int, float))]):
            raise AssertionError('Only equivalent Logs can be concatenated')
        elif self.__key != other.__key:
            raise AssertionError("Only equivalent Logs can be concatenated")

        temp_self = Log(self.__key, self())
        temp_self.add(other())
        return temp_self()


class LogFile(Log):
    def __init__(self, fileName: str, rootDir: str = '.', flip: bool = False):
        self._fileName, self._rootDir, self._flip = f"{splitext(fileName)[0]}.p", rootDir, flip
        self._load()
        super().__init__(splitext(self._fileName)[0], self.data)
        self._update()  # Creates the file it does not exist

    @property
    def _file(self):
        """Exact path to the save file"""
        return abspath(expanduser(join(self._rootDir, self._fileName)))

    def keys(self) -> List[Union[str, int]]:
        """Lists the keys present in the LogFile"""
        return list(self.data.keys())

    def values(self) -> List[Union[Log, dict, int, float, str]]:
        """Lists the Log objects in the LogFile"""
        return list(self.data.values())

    def _data(self) -> Dict[Union[str, int], Union[dict, int, float, str]]:
        return {
            i: self.data[i]() for i in self.keys()
        }

    def __call__(self, *args):
        if args:
            return super().__call__(*args)
        else:
            return self._data()

    def _load(self) -> None:
        if not exists(self._file):
            self.data = {}
        else:
            with open(self._file, 'rb') as p:
                self.data = pickle.load(p) \
                    if not self._flip else revDict(pickle.load(p))  # type: Dict[Union[str, int], Log]

    def _update(self) -> None:
        """Saves full dictionary of {key: Log} as a pickle"""
        os.makedirs(self._rootDir, exist_ok=True)
        with open(self._file, 'wb') as p:
            pickle.dump(self.data if not self._flip else revDict(self.data), p, protocol=pickle.HIGHEST_PROTOCOL)

    @safeLoad
    def add(self, key: Union[dict, List[Union[str, int]], str, int], data: Union[dict, list, str, int, float] = None,
            force: bool = False, string: bool = False) -> None:
        """
        Adds data to the LogFile.

        Args:
            key: The unique key, or list of keys, to call the Log object(s).
            data: Data to add to the LogFile object(s).
            force: Forcefully sets `data` as the value to `key`.
            string: Forcefully stringifies `data` when adding to the LogFile object.
        """
        if isinstance(key, dict):
            for i, j in key.items():
                if i in self.data:
                    self(i).add(j, force)  # Calls the Log object and adds to it
                else:
                    super().add({i: Log(i, j)})  # Creates a Log object and adds to the LogFile
        elif isinstance(key, (str, int)):
            if key in self.data:
                self(key).add(data, force)
            else:
                if force:
                    super().add({key: Log(key, data)}, force)
                else:
                    if string:
                        data = str(data)  # Forcefully adds `data` as a string
                    elif not isinstance(data, (list, dict)):
                        data = [data]  # Forcefully adds `data` as a list if it is not a list, dictionary
                    super().add({key: Log(key, data)})
        elif isinstance(key, list):
            [self.add(k, data, force, string) for k in key]
        else:
            raise TypeError("Data must be <dict>, <list>, <int>, or <str>")

    @safeLoad
    def remove(self, logKey: Union[List[Union[str, int]], str, int],
               keys: Union[List[Union[str, int]], str, int] = None) -> None:
        """
        Removes entries from the data structure.

        Args:
            logKey: The unique key to call the Log object to delete (from).
            keys: Keys to delete from the Log object if the Log object is a dictionary or elements if the Log object
                  is a list or set.
        """
        if not keys:
            super().remove(logKey)
        else:
            if type(logKey) is not list:
                logKey = [logKey]
            [self(i).remove(keys) for i in logKey]

    @safeLoad
    def removeAll(self) -> None:
        """Clears the whole LogFile data structure."""
        if self.data:
            self.remove(self.keys())


def readableLog(fileName: str, rootDir: str = '.') -> str:
    """Creates a human-readable LogFile object in the same directory"""
    fileName = splitext(fileName)[0]
    file = abspath(expanduser(join(rootDir, fileName + '.p')))
    if not exists(file):
        raise FileNotFoundError(f"{file}.p does not exist")
    else:
        data = LogFile(fileName, rootDir)
        with open(file + '.yaml', 'w') as j:
            yaml.safe_dump(data(), j, allow_unicode=True)
        return f"{file}.yaml"


def machinableLog(fileName: str, rootDir: str = '.') -> str:
    """Pickles the human-readable LogFile object into the same directory"""
    fileName = splitext(fileName)[0]
    file = abspath(expanduser(join(rootDir, fileName + '.yaml')))
    if not exists(file):
        raise FileNotFoundError(f"{file}.yaml does not exist")
    else:
        with open(file + '.yaml', 'r') as j:
            data = yaml.safe_load(j)
        dataLog = LogFile(fileName, rootDir)
        dataOld = dataLog()  # type: dict
        dataLog.removeAll()
        try:
            dataLog.add(data)
            return f"{file}.p"
        except Exception as err:
            print(f'ERROR: {err}')
            dataLog.add(dataOld)
            sys.exit(10)

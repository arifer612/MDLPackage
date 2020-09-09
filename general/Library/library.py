import json
import os
import urllib.error
import urllib.request
try:
    import cPickle as pickle
except ImportError:
    import pickle

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


def soup(link, params=None, headers=None, cookies=None, data=None, post=False, JSON=False, response=False,
         timeout=5, attempts=5, **kwargs):
    attempt = 0
    while attempt < attempts:
        try:
            if not post:
                request = requests.get(link, params=params, headers=headers, cookies=cookies, data=data,
                                       timeout=timeout, **kwargs)
            elif int(post) == 1:
                request = requests.post(link, params=params, headers=headers, cookies=cookies, data=data,
                                        timeout=timeout, **kwargs)
            elif int(post) == -1:
                request = requests.patch(link, params=params, headers=headers, cookies=cookies, data=data,
                                         timeout=timeout, **kwargs)

            if not JSON and not response:
                return bs(request.content, 'lxml')
            elif JSON:
                return json.loads(request.content)
            elif response:
                return request
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            attempt += 1
    raise ConnectionRefusedError


def delete(link, params=None, headers=None, data=None, timeout=5):
    requests.delete(link, params=params, headers=headers, data=data, timeout=timeout)


def japaneseDays(day, delimiter=None):
    dayArray = {'月': 'Mon', '火': 'Tue', '水': 'Wed', '木': 'Thu', '金': 'Fri', '土': 'Sat', '日': 'Sun'}
    if not delimiter:
        return dayArray[day]
    else:
        dayLeft, dayRight = day.split(delimiter[0], 1)
        day, dayRight = dayRight.split(delimiter[1], 1)
        return f"{dayLeft}{dayArray[day]}{dayRight}"


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=80, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()


def loadLog(fileName, rootDir, flip=False):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        return {}
    else:
        with open(file, 'rb') as p:
            return pickle.load(p) if not flip else revDict(pickle.load(p))


def writeLog(data, fileName, rootDir, flip=False):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    with open(file, 'wb') as p:
        pickle.dump(data if not flip else revDict(data), p, protocol=pickle.HIGHEST_PROTOCOL)


def toJsonLog(fileName, rootDir):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        raise FileNotFoundError
    else:
        data = loadLog(fileName, rootDir)
        file = os.path.splitext(file)[0] + '.json'
        with open(file, 'w') as j:
            json.dump(data, j, sort_keys=True, indent=4)


def toPickleLog(fileName, rootDir):
    fileName = os.path.splitext(fileName)[0] + '.json'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        raise FileNotFoundError
    else:
        with open(file, 'r') as j:
            data = json.load(j)
        fileName = os.path.splitext(fileName)[0] + '.p'
        writeLog(data, fileName, rootDir)
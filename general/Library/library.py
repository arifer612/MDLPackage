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


def readableLog(fileName, rootDir='.'):
    fileName = os.path.splitext(fileName)[0] + '.p'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        raise FileNotFoundError
    else:
        data = loadLog(fileName, rootDir)
        file = os.path.splitext(file)[0] + '.yaml'
        with open(file, 'w') as j:
            yaml.safe_dump(data, j)
        return f"{file}"


def machinableLog(fileName, rootDir='.'):
    fileName = os.path.splitext(fileName)[0] + '.yaml'
    file = os.path.abspath(os.path.expanduser(os.path.join(rootDir, fileName)))
    if not os.path.exists(file):
        raise FileNotFoundError
    else:
        with open(file, 'r') as j:
            data = yaml.safe_load(j)
        fileName = os.path.splitext(fileName)[0] + '.p'
        saveLog(data, fileName, rootDir)

import json
from os.path import abspath, expanduser, join as j
from typing import Optional, Union

import requests
from bs4 import BeautifulSoup
from requests import Response


def fullpath(file: str, root: str = ".") -> str:
    """Gets full filepath"""
    return abspath(expanduser(j(file, root)))


def revDict(dic: dict) -> dict:
    """Reverses a dictionary order"""
    return dict(reversed(list(dic.items())))


def saveFile(link: str, rootDir: str = ".", fileName: str = "", attempts: int = 3, **kwargs) -> Optional[str]:
    """
    Downloads file and saves locally

    Args:
        link (str): Link of object to download.
        rootDir (str): Directory to save file to.
        fileName (str): Name to save to file as. If not specified, the name will be inferred from `link`.
        attempts (int): Number of attempts to make if link cannot be accessed on the first try.
        kwargs: requests.request() parameters such as `params`, `headers`, `data`, `cookies`, `stream`, `json` etc.

    Returns:
        The full filepath.
    """
    fileName = link.split('/')[-1].replace('-', '_') if not fileName else fileName
    attempts = int(attempts)
    while attempts:
        res = requests.get(link, stream=True, **kwargs)
        if res.status_code == 200:
            with open(fullpath(fileName, rootDir), 'wb') as f:
                for chunk in res.iter_content(1024):
                    f.write(chunk)
            return fullpath(fileName, rootDir)
        else:
            attempts -= 1
    return None


def soup(link: str, post: Union[bool, int] = False, JSON: bool = False, response: bool = False, delete: bool = False,
         parser: str = 'lxml', timeout: int = 5, attempts: int = 5, **kwargs)\
        -> Union[bool, BeautifulSoup, Response, dict]:
    """
    A scraping `requests` alternative. Retrieves information of the website by `requests` and converts it
    to the preferred format, be it a BeautifulSoup, a json dictionary, or just the Response object as is.
    By default soup() will retrieve a BeautifulSoup of the webpage, parsed using `lxml`.

    Args:
        link (str): Link of the website.
        post (bool or int): If True, posts to the webpage with requests.post();
                            if False, retrieves the webpage with requests.get();
                            if -1, patches the webpage with requests.patch().
        JSON (bool): Returns the webpage as a JSON dictionary.
        response (bool): Returns the webpage as a Response object.
        delete (bool): If True, sends a requests.delete() signal to the webpage.
        parser (str): BeautifulSoup parser. It is `lxml` by default.
        timeout (int): Number of seconds to wait for response before forcibly cutting the connection.
        attempts (int): Number of timeout attempts to make before giving up on website.
        kwargs: requests.request() parameters such as `params`, `headers`, `data`, `cookies`, `stream`, `json` etc.

    Returns:
        The webpage response.

    Raises:
        ConnectionError: If a 404 error is raised.
        ConnectionRefusedError: If all attempts have been exhausted with no response from the webpage.
        ValueError: If the wrong value for post is used. It can only be a boolean or -1.
    """
    attempts = int(attempts)
    while attempts:
        try:
            if delete:
                request = requests.delete(link, timeout=timeout, **kwargs)
                return request.status_code == 200  # type: bool

            if not post:
                request = requests.get(link, timeout=timeout, **kwargs)
            elif int(post) == 1:
                request = requests.post(link, timeout=timeout, **kwargs)
            elif int(post) == -1:
                request = requests.patch(link, timeout=timeout, **kwargs)
            else:
                raise ValueError(f"Incorrect post value ({post}). "
                                 f"`requests.get()`: `False`; "
                                 f"`requests.post()`: `True`;"
                                 " `requests.patch()`: `-True`")

            if request.status_code == 404:
                raise ConnectionError

            if not JSON and not response:
                return BeautifulSoup(request.content, parser)  # type: BeautifulSoup
            elif JSON:
                return json.loads(request.content)  # type: dict
            elif response:
                return request  # type: Response
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout):
            attempts -= 1
        except ConnectionError:
            raise ConnectionError("Error 404")
    raise ConnectionRefusedError(f"Could not connect to {link}")


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=80, fill='█', printEnd="\r"):
    """
    Prints a progress bar over an iterable.
    Retrieved from @Greenstick on StackOverFlow in post /questions/3173320
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    # Print New Line on Complete
    if iteration == total:
        print()

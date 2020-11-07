import datetime as d
import json
import os
import re
import random
import string
from configparser import ConfigParser
from distutils.util import strtobool
from getpass import getpass

from requests_toolbelt.multipart.encoder import MultipartEncoder
from requests.cookies import RequestsCookieJar
from typing import Union, Optional, Tuple, List, Dict, Any
from datetime import datetime

from mdl import general as g
from mdl import configFile

siteRoot = 'https://mydramalist.com'
imageURL = f'{siteRoot}/upload/'


def login() -> RequestsCookieJar:
    """MDL login script"""
    loginKey = ConfigParser()
    loginKey.read(configFile._Config__keyDir)
    loginKeys = (loginKey['USER']['username'], loginKey['USER']['password'])

    def userInfo() -> Tuple[str, str]:
        """Retrieves username and password"""
        username = input('USERNAME >>>')
        password = getpass('PASSWORD >>>')
        return username, password

    def saveKeys(newKeys: Tuple[str, str]) -> None:
        """Queries user to save login keys locally"""
        if loginKeys not in [newKeys, ('-', '-')]:
            answer = input('Save login details? (y/n)')
            if strtobool(answer) or not answer:
                loginKey['USER']['username'], loginKey['USER']['password'] \
                    = newKeys
                with open(configFile._Config__keyDir, 'w') as f:
                    loginKey.write(f)
                    print('Saved login details in keyfile')

    def loginFail(loginDetails: Tuple[str, str]) -> Tuple[Tuple[str ,str], Optional[RequestsCookieJar]]:
        """Script to inspect if logged-in successfully"""
        response = g.soup(f'{siteRoot}/signin', data={'username': loginDetails[0], 'password': loginDetails[1]},
                          post=True, response=True)
        cookie = response.request._cookies  # type: Optional[RequestsCookieJar]
        if cookie.get('jl_sess'):  # Successfully logged-in
            saveKeys(loginDetails)
        else:
            cookie = None
            print('!!Incorrect email or password!!')
            loginDetails = userInfo()
            print("Attempting to login again\n...")
        return loginDetails, cookie

    details = userInfo() if not all(loginKeys) else loginKeys

    cookies, attempt = None, 0
    attempt += not all(loginKeys)
    while not cookies and attempt < 3:
        details, cookies = loginFail(details)
        attempt += 1
    if not cookies and attempt == 3:
        print('Failed to login\nCheck username and password again.')
    else:
        print('Successfully logged in')
    return cookies


def parameters(cookies: RequestsCookieJar, undef: bool = False, inverse: bool = False) -> Dict[str, str]:
    """Prepares `request` parameters for requesting/posting/patching.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        undef (bool): True -> lang = undefined; False -> lang = en-US
        inverse (bool): Reverses parameter if True.
    """
    params = {
        'lang': 'en-US' if not undef else 'undefined',
        'token': cookies.get('jl_sess')
    }
    return params if not inverse else g.revDict(params)


def search(keyword, result: int = None) -> str:
    """Extracts MDL link by searching MDL for keyword.

    Args:
        keyword (str): Search keyword.
        result (int): Prepared result index.
    """
    searchResults = g.soup(f"{siteRoot}/search", params={'q': keyword}).find_all('h6')

    try:
        if len(searchResults) == 1:
            link = f"{siteRoot}{searchResults[0].contents[0]['href']}"
        elif len(searchResults) > 1:
            try:
                if result:
                    link = f"{siteRoot}{searchResults[result - 1].contents[0]['href']}"
                else:
                    raise IndexError
            except IndexError:
                if result:
                    print('Declared index does not exist. Pick one of the following shows')
                else:
                    print('Which of these shows is the right show?')
                for resultNumber, result in enumerate(searchResults, start=1):
                    print(f"{resultNumber} : "
                          f"{result.contents[0].text} ({result.find_next(class_='text-muted').text})")
                counter = 1
                while True:
                    try:
                        answer = int(input())
                        if answer - 1 not in range(len(searchResults)):
                            raise ValueError
                        else:
                            break
                    except ValueError:
                        counter += 1
                        if counter < 4:
                            print('Invalid answer. Pick one of the shows above')
                        else:
                            print('Too many invalid answers. The first show will be picked')
                            answer = 1
                            break
                link = f"{siteRoot}{searchResults[answer - 1].contents[0]['href']}"
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        link = ''
        print('Search keyword returns no results. Check search keyword again')
    return link


def getShowID(link) -> str:
    """Extracts information of the show ID from the link."""
    return link.split('/')[-1].split('-')[0]


def showDetails(link) -> Tuple[str, str, int]:
    """Extracts information of the show's original network and total posted episodes on MDL.

    Args:
        link (str): Link to the show on MDL.

    Returns:
        Native title of the show on MDL.
        Network channel of the show on MDL.
        Total number of episodes posted on MDL.

    Raises:
        ConnectionError: If the link does not direct to a valid site on MDL.
        ConnectionRefusedError: If the server to MDL could not be contacted.
    """
    soup = g.soup(link)
    try:
        nativeTitle = soup.find('b', text='Native Title:').find_next('a')['title']
    except AttributeError:  # No native tile in MDL
        nativeTitle = ''
    try:
        network = soup.find(string='Original Network:').find_next('a').string
    except AttributeError:
        network = ''
    totalEpisodes = int(list(soup.find(string='Episodes:').parent.parent.strings)[-1])
    return nativeTitle, network, totalEpisodes


def getStartDate(link: str, totalEpisodes: int = None, startEpisode: int = 1) -> datetime:
    """Gets the episode air date. only works if there is at least 1 date posted on MDL.

    Args:
        link (str): MDL link.
        totalEpisodes (int): Total number of episodes on MDL.
        startEpisode (int): If specified, gets start date of episode.

    Returns:
        Start date

    Raises:
        ConnectionError: If the link does not direct to a valid site on MDL.
        ConnectionRefusedError: If the server to MDL could not be contacted.
        AttributeError: If all the episodes do not have a start date.
    """
    def getAirDate(episode: int) -> datetime:
        if episode == 1:
            aired = g.soup(link).find(xitemprop='datePublished')['content']
            return d.datetime.strptime(aired, '%Y-%m-%d')
        else:
            soup = g.soup(f"{link}/episodes")
            searchTerm = f"{soup.find(property='og:title')['content']} Episode {startEpisode - 1}"
            aired = soup.find(string=searchTerm).find_next(class_='air-date').string
            return d.datetime.strptime(aired, '%b %d, %Y')

    totalEpisodes = totalEpisodes if totalEpisodes else showDetails(link)[1]
    attempt = 0
    while attempt < 3:
        while 0 < startEpisode <= totalEpisodes:
            try:
                return getAirDate(startEpisode)
            except ValueError:
                startEpisode -= 1
                if startEpisode > 0:
                    print(f"Invalid airdate for Episode {startEpisode + 1}. Checking Episode {startEpisode}")
                else:
                    print('No information for any episodes at all. Provide information of the first aired episode')
                    while True:
                        try:
                            return d.datetime.strptime(input('YYYY/MM/DD : '), '%Y/%m/%d')
                        except ValueError:
                            pass
        try:  # Fixes startEpisode if it is above the total number of posted episodes
            print('Invalid start episode.')
            startEpisode = int(input('>>>'))
        except ValueError:
            attempt += 1
    raise AttributeError("No start dates found.")


def getEpisodeID(link: str, episodeNumber: int) -> int:
    """Extracts episode ID of a show's episode.

    Args:
        link (str): MDL link.
        episodeNumber (int): Episode number.

    Returns:
        Episode ID

    Raises:
        FileNotFoundError: If the episode does not exists on MDL.
    """
    try:
        episodeSoup = g.soup(f"{link}/episode/{int(episodeNumber)}")
        return int(episodeSoup.find(property='mdl:rid')['content'])
    except (TypeError, ValueError):
        print(f'Invalid episode (Episode {episodeNumber})')
        raise FileNotFoundError(f"Episode {episodeNumber} does not exists in MDL.")


def retrieveRatings(cookies: RequestsCookieJar, link: str, start: int = 1, end: Optional[int] = None)\
        -> Dict[int, Dict[str, Union[Tuple[int, int], Dict[str, float], str]]]:
    """Retrieves rating information of a show on MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        link (str): MDL link.
        start (int): Episode to start retrieval.
        end (int): Episode to stop retrieval. If unspecified, it will retrieve the rating of 1 episode.

    Returns:
        {episodeNumber:
            {'ID': (episodeID, ratingID),
             'rating':
                {'self': User-rating, 'MDL': Average-rating},
             'url': episodeRatingURL
            }
        }
    """
    end = end if end else start
    rating = {}
    episodeSoup = g.soup(f"{link}/episodes")
    for episodeNumber in range(start, end + 1):
        try:
            episodeID = getEpisodeID(link, episodeNumber)
            ratingURL = f"{siteRoot}/v1/episodes/{getEpisodeID(link, episodeNumber)}/reviews/check/rating"
            ratingJSON = g.soup(ratingURL, params=parameters(cookies), cookies=cookies, JSON=True)
            rating[episodeNumber] = {
                'ID': (
                    episodeID,
                    ratingJSON['id']
                ),
                'rating': {
                    'self': ratingJSON['rating'],
                    'MDL': float(episodeSoup.find(href=f"{link.replace(siteRoot, '')}/episode/{episodeNumber}")
                                 .find_next(class_='rating-panel').find('b').string)
                },
                'url': ratingURL.replace('/check/rating', '')
            }
        except FileNotFoundError:
            pass
    return rating


def postRating(cookies: RequestsCookieJar,
               episodeRating: Dict[str, Union[Tuple[int, int], Dict[str, Union[int, float]], str]],
               details: Dict[str, Union[int, float, str]] = None) -> bool:
    """Post personal ratings to MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        episodeRating (dict): Basic rating information required to post to MDL. Same structure as the return of
                              retrieveRating()
        details (dict): [DEPRECATED] More detailed information to include into the rating. The possible keys are:
                        `dropped`, `spoiler`, `completed`, `episode_seen`, `review_headline`, `story_rating`,
                        `acting_rating`, `music_rating`, `rewatch_rating`, `overall_rating`

    Returns:
        Boolean result of the successful post/patch.
    """
    if details:
        from warnings import warn
        warn("`details` does not seem to be supported in MDL anymore.", DeprecationWarning, stacklevel=2)
    else:
        details = {}
    post = True if episodeRating['ID'][1] == 0 else False
    if post:
        formData = {
            'id': 0,
            'dropped': '',
            'spoiler': '',
            'completed': '',
            'episode_seen': '',
            'review_headline': '',
            'review': '',
            'story_rating': 0,
            'acting_rating': 0,
            'lang_iso': 'en_US',
            'music_rating': 0,
            'rewatch_rating': 0,
            'overall_rating': 0,
            'rating': round(episodeRating['rating']['self'] * 2) / 2
        }
    else:
        formData = {
            'id': episodeRating['ID'][1],
            'lang_iso': 'en-US',
            'language': 'English',
            'headline': '',
            'review': '',
            'review_raw': '',
            'rating': round(episodeRating['rating']['self'] * 2) / 2
        }

    formData.update(details)
    ratingURL = episodeRating['url'] + (not post) * f"/{episodeRating['ID'][1]}"
    response = g.soup(ratingURL, data=formData, params=parameters(cookies, undef=False), cookies=cookies,
                      post=(-1) ** (not post), response=True)
    return response.status_code == 200


def postURL(showID: Optional[str] = None, epID: Optional[int] = None) -> str:
    """Preps URL to post information to."""
    return f"{siteRoot}/v1/edit/episodes/{epID}" if epID else f"{siteRoot}/v1/edit/titles/{showID}/"


def showInfo(cookies: RequestsCookieJar, link: str)\
        -> Tuple[dict, dict, Dict[Union[str, int], dict], Dict[str, Tuple[str, str, str, int]]]:
    """Parses all the information of the show episodes and season from MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        link (str): Link to the show.

    Returns:
        info (dict): Latest JSON dictionary for the show information on MDL.
        releases (dict): Latest JSON dictionary for the show releases on MDL.
        episodes (dict): Full dictionary of all the episodes posted on MDL.
        seasons (dict): Full dictionary of all the seasons posted on MDL.
    """
    def checkUpdates(jsonResponse: Dict[str, dict], onlyEpisodes: bool = False) -> dict:
        original = jsonResponse['original']
        revision = jsonResponse['revision']
        revised = 0
        if not onlyEpisodes:
            for element in revision.values():
                revised += not not element
            return original if revised == 0 else revision
        else:
            return revision['episodes'] if not not revision['episodes'] else original['episodes']

    showID = getShowID(link)
    infoURL, releaseURL = [postURL(showID=showID) + i for i in ['', '/release']]  # type: str, str
    params = parameters(cookies)
    episodesURL = f"{infoURL}/episodes"

    info = checkUpdates(g.soup(infoURL, params=params, cookies=cookies, JSON=True))
    releases = checkUpdates(g.soup(releaseURL, params=params, cookies=cookies, JSON=True))

    seasons = {
        season['name']: (
            season['sid'],
            season['episode_start'],
            season['episode_end'],
            order
        ) for order, season in enumerate(releases['seasons'])
    }

    episodesList = []
    for sID, startEpisode, endEpisode, order in seasons.values():
        params.update({
            'sid': sID,
            'eps': startEpisode,
            'epe': endEpisode
        })
        episodesList.append(
            checkUpdates(
                g.soup(episodesURL, params=params, cookies=cookies, JSON=True),
                onlyEpisodes=True)
        )
    episodes = {info['episode_number']: info for season in episodesList for info in season}
    episodes = {keys: episodes[keys] for keys in sorted(list(episodes.keys()))}
    return info, releases, episodes, seasons


def castInfo(cookies: RequestsCookieJar, link: str) -> Tuple[dict, dict, str, str, dict]:
    """Parses all the information of the cast of the show from MDL

    Args:
        cookies (RequestsCookieJar): Login cookies.
        link (str): Link to the show.

    Returns:
         castList (dict): Full dictionary of all the show cast on MDL.
         castRevision (dict): Latest JSON dictionary of updated show cast on MDL.
         weights (str): Weighted order of show cast on MDL.
         castURL (str): Redirect link to update the show cast on MDL.
         params (dict): Request parameters to update the show cast on MDL.
    """
    showID = getShowID(link)
    castURL = postURL(showID=showID) + 'cast'
    params = parameters(cookies)
    castJSON = g.soup(castURL, params=params, cookies=cookies, JSON=True)
    castOriginal = {castValue['display_name']: castValue for castValue in castJSON['original']['cast']}
    castRevision = {castValue['display_name']: castValue for castValue in castJSON['revision']['cast']}
    castList = {
        cast: castRevision[cast] if cast in castRevision else castOriginal[cast] for cast in castOriginal
    }
    weights = ','.join(castJSON['revision']['cast_weights'])
    return castList, castRevision, weights, castURL, params


def castSearch(name, nationality=None, gender=None) -> Optional[int]:
    """Searches for cast ID of a cast on MDL.

    Args:
        name (str): Name of cast to search
        nationality (str): Filter search by nationality. If not specified, the filter will not be applied.
                           The available nationalities on MDL are `jp`, `ko`, `cn`, `hk`, `tw`, `th`, and `fp`.
        gender (str): Filter search by gender. If not specified, the filter will not be applied.
                      The available genders on MDL are `m`, and `f` only.

    Returns:
         Cast ID
    """
    nationalityMap = {
        'japanese': 1,
        'jp': 1,
        'korean': 2,
        'ko': 2,
        'chinese': 3,
        'cn': 3,
        'hong kongers': 4,
        'hk': 4,
        'taiwanese': 5,
        'tw': 5,
        'thai': 6,
        'th': 6,
        'filipino': 140,
        'fp': 140
    }
    genderMap = {
        'male': 77,
        'm': 77,
        'female': 70,
        'f': 70
    }
    params = {
        'q': name,
        'adv': 'people',
        'gd': genderMap[gender.lower()] if gender else None,
        'na': nationalityMap[nationality.lower()] if nationality else None,
        'so': 'relevance'
    }
    [params.pop(i, None) for i in [j for j in params if not params[j]]]
    searchResults = g.soup(f"{siteRoot}/search", params=params).find_all('h6')

    try:
        if len(searchResults) > 1:
            print(f'Which of these is the right cast for {name}? (0 if no matches)')
            for resultNumber, result in enumerate(searchResults, start=1):
                print(f"{resultNumber} : {result.contents[0].text} "
                      f"({result.find_next(class_='text-muted').find_next('p').string})")
            counter = 1
            while True:
                try:
                    answer = int(input())
                    if answer == 0:
                        raise FileNotFoundError
                    elif answer not in range(len(searchResults)):
                        raise ValueError
                    else:
                        return int(searchResults[answer - 1].string)
                except ValueError:
                    counter += 1
                    if counter < 4:
                        print('Invalid answer')
                    else:
                        print('Too many invalid answers. The first choice will be picked')
                        return int(searchResults[0].string)
        elif len(searchResults) == 1:
            return int(searchResults[0].string)
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        return None


def castAnalyse(castList: Dict[str, dict], castRevision: Dict, castDict: Dict[str, List[int]]) -> List[dict]:
    """Analyses the new cast against latest posted cast on MDL

    Args:
        castList (dict): Currently posted cast list on MDL.
        castRevision (dict): Latest updates to cast list on MDL.
        castDict (dict): Dictionary of cast members and a list of episodes they starred in.
                         e.g. {'cast1': [1, 2, 4, 5, 6], 'cast2': ...}

    Returns:
        A list of cast members with valid changes to post to MDL.
    """

    # Parses castDict into the same format as castList.
    castEdited = {}  # type: Dict[str, str]
    for cast, episodeList in castDict.items():
        end = -1
        final = []
        for episode in episodeList:
            if episode > end + 1:
                final.append(str(episode))
            else:
                final[-1] = final[-1].split('-')[0] + f'-{episode}'
            end = episode
        castEdited[cast] = f"(Ep {', '.join([episodeBunch for episodeBunch in final])})"

    # Compares castEdited against castList and castRevision. Only cast with changes are picked up.
    newCast = []
    for cast, castDetails in castList.items():
        try:
            characterName = castDetails['character_name']
            if characterName:
                episodes = re.findall(r'\(Ep.*?\)', characterName)
                if episodes:
                    episodes = f"({episodes[0]})"
                    episodesNormalised = episodes.replace('Ep. ', 'Ep ').replace('Ep.', 'Ep ')
                    if episodesNormalised != castEdited[cast]:
                        castDetails['character_name'] = castDetails['character_name'].replace(episodes, castEdited[cast])
                    else:
                        raise KeyError
                else:
                    castDetails['character_name'] = f"{characterName} {castEdited[cast]}"
            else:
                castDetails['character_name'] = castEdited[cast]
            newCast.append(castDetails)
        except KeyError:  # Ignore unexpected cast who were probably not considered in castEdited
            pass
    for guest, guestDetails in set(castRevision) - set(castList):
        newCast.append(guestDetails)
    return newCast


def castSubmit(cookies: RequestsCookieJar, link: str, latestCast: dict, notes: str = '') -> None:
    """Posts the updated cast list to MDL

    Args:
        cookies (RequestsCookieJar): Login cookies.
        link (str): Show link.
        latestCast (dict): Dictionary of cast members and a list of episodes they starred in.
                           e.g. {'cast1': [1, 2, 4, 5, 6], 'cast2': ...}
        notes (str): Notes for the reviewing staff to read.
    """
    castList, castRevision, weights, castURL, params = castInfo(cookies, link)
    newCastList = castAnalyse(castList, castRevision, latestCast)
    if newCastList:
        popTerms = ['url', 'content_type', 'display_nam', 'role_id', 'weight', 'thumbnail']
        [item.pop(i, None) for item in newCastList for i in popTerms]
        dataForm = {
            'notes': notes,
            'category': 'cast',
            'cast_data': json.dumps(newCastList),
            'weights': weights,
            'cast_weights': weights
        }
        response = g.soup(castURL, data=dataForm, params=params, cookies=cookies, post=True, response=True)
        if response.status_code == 200:
            print('Updated cast')
        else:
            print('Failed to update cast')
    else:
        print('No updates')


def imageSubmit(cookies: RequestsCookieJar, link: str, file: str, fileDir: str, keyNotes: str,
                epID: Optional[int] = False, description: str = '', suppress: bool = False) -> bool:
    """Posts an image to MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        link (str): Show link.
        file (str): Filename with its extension.
        fileDir (str): Directory to where the file is stored in.
        keyNotes (str): Title of the image if uploading a photo or notes for the approving staff to read if uploading
                        an episode cover.
        epID (str): Episode ID if uploading an episode cover. If not specified, the image will upload as a normal
                    photo by default.
        description (str): Description of a photo. Only if the image is uploaded as normal photo.
        suppress (bool): Refrains from printing any information.

    Returns:
        True if the image has been posted and False otherwise.
    """

    # Upload to MDL
    try:
        params = parameters(cookies, undef=not not epID)
        imageData = MultipartEncoder(
            fields={
                'category': (None, 'temp_photos'),
                'file': (file, open(os.path.join(fileDir, file), 'rb'), 'image/jpeg')
            },
            boundary=f"------WebKitFormBoundary{''.join(random.sample(string.ascii_letters + string.digits, 16))}"
        )
        headers = {'content-type': imageData.content_type}
        uploadResponse = g.soup(imageURL, params=params if epID else None, headers=headers,
                                cookies=cookies, data=imageData, post=True, response=True)
        imageID = json.loads(uploadResponse.content).get('filename')  # type: str

        if not imageID:
            raise ConnectionRefusedError

        # Submit to MDL
        if not epID:
            dataForm = {
                'title': keyNotes,
                'image': f'https://i.mydramalist.com/{imageID}m.jpg',
                'description': description,
                'filename': imageID
            }
        else:
            dataForm = {
                'category': 'cover',
                'notes': keyNotes,
                'cover_id': imageID
            }
        submitURL = postURL(getShowID(link), epID).replace('edit/', '' if not epID else 'edit/') \
                    + ('/photos' if not epID else '/cover')
        params = g.revDict(params) if not epID else params
        attempt = 0
        while attempt < 3:
            submitResponse = g.soup(submitURL, data=dataForm, params=params, cookies=cookies,
                                    post=True, response=True)
            if submitResponse.status_code == 200:
                print(f'Posted {file}') if not suppress else True
                os.remove(os.path.join(fileDir, file))
                return True
            else:
                attempt += 1
        raise ConnectionRefusedError
    except (ConnectionRefusedError, AttributeError):  # AttributeError : Images that do not exist
        print(f'Failed to post {file}')
        return False


def retrieveSummary(cookies: RequestsCookieJar, epID: int) -> Dict[str, str]:
    """Retrieves the episode summary from MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        epID (str): Episode ID.

    Returns:
        A dictionary with the episode title and summary.
    """
    summaryURL = postURL(epID=epID)
    response = g.soup(summaryURL, params=parameters(cookies, undef=True), cookies=cookies, JSON=True)['revision']
    return {'title': response['title'], 'summary': response['summary']}


def summarySubmit(cookies: RequestsCookieJar, epID: int, summary: str = '', title: str = '', notes: str = ''):
    """Updates the episode summary on MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        epID (str): Episode ID.
        summary (str): Episode summary text.
        title (str): Episode title test.
        notes (str): Notes for the reviewing staff to read.

    Returns:
        True if the information was successfully posted to MDL and False otherwise.
    """
    if summary or title:
        dataForm = {
            'category': 'details',
            'notes': notes,
            'summary': summary,
            'title': title
        }
        submitURL = postURL(epID=epID) + '/details'
        response = g.soup(submitURL, data=dataForm, params=parameters(cookies, undef=True), cookies=cookies,
                          post=True, response=True)
        if response.status_code == 200:
            return True
        else:
            print(f'Failed to update {epID}')
            return False
    else:
        return False


def externalLinksSubmit(cookies: RequestsCookieJar, link: str, externalLinks: List[Dict[str, str]], notes: str = '') \
        -> bool:
    """Posts new external links for a show on MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        link (str): Link to the show on MDL.
        externalLinks (list): List of external links, each formatted as a dictionary.
        notes (str): Notes for reviewing staff to read.
        Examples:
        externalLinks = [
            {
               "key": "website",
               "label": "Official site (MBS)",
               "text": "",
               "type": "uri",
               "value": "https://www.mbs.jp/araoto_drama/",
               "_status": "created"
           },
           {
               "key": "twitter",
               "label": "",
               "text": "",
               "type": "social",
               "value": "araoto_drama",
               "_status": "created"
           }
        ]

    """
    if externalLinks:
        submitURL = postURL(showID=getShowID(link)) + 'details'
        params = parameters(cookies)
        dataForm = {
            'external_links': externalLinks,
            'category': 'external_links',
            'notes': notes
        }
        response = g.soup(submitURL, params=params, cookies=cookies, data=dataForm, post=True, response=True)
        return True if response.status_code == 200 else False
    else:
        return True


def deleteSubmission(cookies: RequestsCookieJar, category: str, link: str = '', epID: Optional[int] = None) -> bool:
    """Deletes a submission on MDL.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        category (str): Category of submission to delete.
                        e.g. cast, image etc.
        link (str): Link to the show on MDL.
        epID (str): Episode ID

    Returns:
        True if deletion is successful and False otherwise.
    """
    if category:
        deleteURL = f"{siteRoot}/v1/edit/tickets/{epID}/episodes" \
            if epID else f"{siteRoot}/v1/edit/titles/{getShowID(link)}/titles"
        params = {
            'category': category
        }
        params.update(parameters(cookies, undef=True if epID else False))
        return g.soup(deleteURL, params=params, delete=True)
    else:
        raise SyntaxError


def userProfile(cookies: RequestsCookieJar) -> str:
    """Gets user's MDL ID

    Args:
        cookies (RequestsCookieJar): Login cookies.
    """
    profile = g.soup(f"{siteRoot}/profile", cookies=cookies)
    return re.match(".+(?='s Profile)", profile.head.title.string)[0]


def dramaList(cookies: RequestsCookieJar, suppress: bool = False, *args) -> Dict[str, Dict[int, Dict[str, Any]]]:
    """Parses user's drama list and returns it as a navigable dictionary.

    Args:
        cookies (RequestsCookieJar): Login cookies.
        suppress (bool): Hides progress bar if True.
        args: Categories of shows in the user's drama list to filter.
              The available categories are `watching`, `completed,` plan_to_watch`, `hold`, `drop`, `not_interested`

    Returns:
        The user's drama list as a dictionary.
    """
    if not args:
        args = ('watching', 'completed', 'plan_to_watch', 'hold')  # Default settings
    profileLink = f"{siteRoot}/profile"
    params = parameters(cookies)
    listLink = f"{siteRoot}{g.soup(profileLink, cookies=cookies).find('a', text='My Watchlist')['href']}"
    listSoup = g.soup(listLink, cookies=cookies)
    lists = {
        'Watching': listSoup.find(id='list_1') if 'watching' in args else None,
        'Completed': listSoup.find(id='list_2') if 'completed' in args else None,
        'Plan to watch': listSoup.find(id='list_3') if 'plan_to_watch' else None,
        'On hold': listSoup.find(id='list_4') if 'hold' else None,
        'Dropped': listSoup.find(id='list_5') if 'drop' else None,
        'Not interested': g.soup(f"{listLink}/not_interested", cookies=cookies).find(id='list_6')
        if 'not_interested' else None
    }

    def userInfo(ID: int) -> Dict[str, Optional[datetime, int]]:
        infoSoup = g.soup(f"{siteRoot}/v1/users/watchaction/{ID}",
                          params=parameters,
                          cookies=cookies,
                          JSON=True)['data']
        return {
            'Started on': None if infoSoup['date_start'] == '0000-00-00'
            else d.datetime.strptime(infoSoup['date_start'], '%Y-%m-%d'),
            'Ended on': None if infoSoup['date_finish'] == '0000-00-00'
            else d.datetime.strptime(infoSoup['date_finish'], '%Y-%m-%d'),
            'Re-watched': infoSoup['times_rewatched']
        }

    for key in [i for i in lists if lists[i]]:
        try:
            lists[key] = {
                int(show['id'][2:]): {
                    'Title': show.find(class_='title').text,
                    'Country of Origin': show.find(class_='sort2').text,
                    # 'year': int(show.find(class_='sort3').text),
                    'Show type': show.find(class_='sort4').text,
                    'Rating': float(show.find(class_='score').text)
                    if show.find(class_='score') or float(show.find(class_='score').text) != 0.0 else None,
                    'Episodes watched': int(show.find(class_='episode-seen').text)
                    if show.find(class_='episode-seen') else 0,
                    'Total episodes': int(show.find(class_='episode-total').text)
                    if show.find(class_='episode-seen') else 0,
                } for show in lists[key].tbody.find_all('tr')
            }
        except (AttributeError, KeyError):
            lists[key] = None
    totalShows = len([i for j in lists if lists[j] for i in lists[j]])
    for key in [i for i in lists if lists[i]]:
        for i, showID in enumerate(lists[key], start=i + 1 if 'i' in locals() else 1):
            lists[key][showID].update(userInfo(showID))
            g.printProgressBar(i, totalShows, prefix=f'Retrieving {i}/{totalShows}') if not suppress else True
    return lists

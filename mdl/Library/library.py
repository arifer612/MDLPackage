import datetime as d
import json
import os
import random
import string
from configparser import ConfigParser
from distutils.util import strtobool
from getpass import getpass

from requests_toolbelt.multipart.encoder import MultipartEncoder

from mdl import general as g
from mdl import configFile

siteRoot = 'https://mydramalist.com'
imageURL = f'{siteRoot}/upload/'


## Login script
def login():
    loginKey = ConfigParser()
    loginKey.read(configFile._Config__keyDir)
    loginKeys = (loginKey['USER']['username'], loginKey['USER']['password'])

    def userInfo():  # Retrieves username and password
        username = input('USERNAME >>>')
        password = getpass('PASSWORD >>>')
        return username, password

    def saveKeys(newKeys):
        if loginKeys not in [newKeys, ('-', '-')]:
            answer = input('Save login details? (y/n)')
            if strtobool(answer) or not answer:
                loginKey['USER']['username'], loginKey['USER']['password'] \
                    = newKeys
                with open(configFile._Config__keyDir, 'w') as f:
                    loginKey.write(f)
                    print('Saved login details in keyfile')

    def loginFail(loginDetails):
        response = g.soup(f'{siteRoot}/signin', data={'username': loginDetails[0], 'password': loginDetails[1]},
                          post=True, response=True)
        try:
            cookie = response.request._cookies
            if 'jl_sess' in cookie:
                saveKeys(loginDetails)
            else:
                raise ConnectionError
        except ConnectionError:
            cookie = None
            print('!!Incorrect email or password!!')
            loginDetails = userInfo()
            print("Attempting to login again\n...")
        return loginDetails, cookie

    details = userInfo() if not all(loginKeys) else loginKeys

    cookies = attempt = 0
    attempt += not all(loginKeys)
    while not cookies and attempt < 3:
        details, cookies = loginFail(details)
        attempt += 1
    if not cookies and attempt == 3:
        print('Failed to login\nCheck username and password again.')
    else:
        print('Successfully logged in')
    return cookies


## Prepares parameters and headers for requesting / posting
# cookies (list) : CookieJar. Obtained from login()
# refererURL (str) : Referer URL.
# post (bool) : True -> Prepare headers for posting. False -> Prepares headers for requesting
# undef (bool) : True -> lang = undefined. False -> lang = en-US
def parameters(cookies, undef=False, inverse=False):
    params = {
        'lang': 'en-US' if not undef else 'undefined',
        'token': cookies['jl_sess']
    }
    return params if not inverse else g.revDict(params)


## Extracts MDL links and native title from MDL search
# keyword (str) : Search keyword
# results (int) : Prepared result index
def search(keyword, result=None):
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


def getShowID(link):
    return link.split('/')[-1].split('-')[0]


## Extracts information of show's original network and total posted episodes on MDL
# link (str) : Redirect link. Obtained from search()
def showDetails(link):
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


## Gets episode airdate. Will only work if there is at least 1 date posted on MDL.
# link (str) : Redirect link. Obtained from search()
# totalEpisodes (int) : Total number of episodes posted on MDL. Obtained from showDetails()
# startEpisode (int) : default to be set at 1. May use getStartEpisode() to query user.
def getStartDate(link, totalEpisodes=None, startEpisode=1):
    def getAirDate(episode):
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
    raise UnboundLocalError


## Extracts episode ID of a show's episode
# link (str) : Redirect link. Obtained from search()
# episodeNumber (int) : Episode number
def getEpisodeID(link, episodeNumber):
    try:
        episodeSoup = g.soup(f"{link}/episode/{int(episodeNumber)}")
        return int(episodeSoup.find(property='mdl:rid')['content'])
    except (TypeError, ValueError):
        print(f'Invalid episode (Episode {episodeNumber})')
        raise FileNotFoundError


## Retrieves rating information of a show
# cookies (CookieJar) : Login cookies. Obtained from login()
# link (str) : Redirect link. Obtained from search()
# start (int) : Episode to start retrieving information from
# end (int) : Episode to stop retrieving information from. If not specified, will only retrieve the rating of 1 episode
def retrieveRatings(cookies, link, start=1, end=False):
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


## Post personal ratings onto MDL
# episodeRating (dict) : Information of the episode's rating. Obtained by picking an episode from retrieveRating()
# cookies (CookieJar) : Login cookies. Obtained from login()
# link (str) : Redirect link. Obtained from search()
# details (dict) : Detailed information of rating breakdown.
def postRating(cookies, episodeRating, details=None):
    details = details if details else {}
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
    return True if response.status_code == 200 else False


## Preps URL to post information to
# showID (str) : ShowID. Obtained from getShowID()
# epID (str) : EpisodeID. Obtained from getEpisodeID()
def postURL(showID=None, epID=None):
    return f"{siteRoot}/v1/edit/episodes/{epID}/" if epID else f"{siteRoot}/v1/edit/titles/{showID}/"


## Reads all the information of the show episodes and seasons
# cookies (CookieJar) : Login cookies. Obtained from login()
# showID (str) : ShowID. Obtained from search()
def showInfo(cookies, link):
    def checkUpdates(jsonResponse, onlyEpisodes=False):
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
    infoURL, editURL = [postURL(showID=showID) + i for i in ['', 'release']]
    params = parameters(cookies)
    episodesURL = f"{infoURL}/episodes"

    info = checkUpdates(g.soup(infoURL, params=params, cookies=cookies, JSON=True))
    edit = checkUpdates(g.soup(editURL, params=params, cookies=cookies, JSON=True))

    seasons = {
        season['name']: (
            season['sid'],
            season['episode_start'],
            season['episode_end'],
            order
        ) for order, season in enumerate(edit['seasons'])
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
    return info, edit, episodes, seasons


## Reads all the information of the cast appearance
# cookies (CookieJar) : Login cookies. Obtained from login()
# showID (str) : ShowID. Obtained from search()
def castInfo(cookies, link):
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


## Searches for castID on MDL
def castSearch(name, nationality=None, gender=None):
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
                        return searchResults[answer - 1].string
                except ValueError:
                    counter += 1
                    if counter < 4:
                        print('Invalid answer')
                    else:
                        print('Too many invalid answers. The first choice will be picked')
                        return searchResults[0].string
        elif len(searchResults) == 1:
            return searchResults[0].text
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        return False


## Analyses new cast against previously posted cast on MDL castList (dict) : Cast List. Obtained from castInfo()
# castEdited (dict) : New cast with the appropriate character names castRevision (dict) : Posted revised cast list.
# Obtained from castInfo() (Necessary to make sure the output does not break)
# How this works - It compares the latest cast list against the original posted cast list on MDL.
#   All the cast in the new cast list with a different character name entry will be outputted to be posted to MDL.
#   This was created mainly for variety shows with guests, where they only appear for a few episodes at a time.
def castAnalyse(castList, castEdited, castRevision):
    newCast = []
    for cast, castDetails in castList.items():
        try:
            characterName = castDetails['character_name'].replace('(Ep. ', '(Ep ').replace('(Ep.', '(Ep ')
            if characterName:
                episodes = characterName[characterName.find('(Ep '):]
                episodes = episodes[:episodes.find(')') + 1]
                if episodes and episodes != castEdited[cast]:
                    castDetails['character_name'] = castDetails['character_name'].replace(episodes, castEdited[cast])
                elif not episodes:
                    castDetails['character_name'] = f"{characterName} {castEdited[cast]}"
                else:
                    raise KeyError
            else:
                castDetails['character_name'] = castEdited[cast]
            newCast.append(castDetails)
        except KeyError:  # Ignore guests that may not be considered in castEdited
            pass
    for guest, guestDetails in set(castRevision) - set(castList):
        newCast.append(guestDetails)
    return newCast


## Posts the updated cast list onto MDL
# link (str) : Link to show on MDL. Obtained from search()
# showID (str) : Show ID. Obtained from search()
# latestCast (dict) : Analysed cast list. Obtained from g.episodesAnalyse()
# notes (str) : Notes for reviewing staff to read
def castSubmit(cookies, link, latestCast, notes=''):
    castList, castRevision, weights, castURL, params = castInfo(cookies, link)
    newCastList = castAnalyse(castList, latestCast, castRevision)
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
            return True
        else:
            print('Failed to update cast')
            return False
    else:
        return True


## Uploads images to MDL
# cookies (CookieJar) : Login cookies. Obtained from login()
# link (str) : Link to show on MDL. Obtained from search()
# file (str) : Filename with extension
# fileDir (dir) : Directory where file is stored in
# keyNotes (str) : Title of photo if uploading photo or notes for approving staff to read if uploading episode cover
# epID (str) : Episode ID if uploading as episode cover, otherwise will automatically upload as a normal photo
# description (str) : Only used if uploading photo to a show
def imageSubmit(cookies, link, file, fileDir, keyNotes, epID=False, description='', suppress=False, attempts=3):
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
        imageID = None
        attempt = 0
        while attempt < attempts:
            uploadResponse = g.soup(imageURL, params=params if epID else None, headers=headers,
                                    cookies=cookies, data=imageData, post=True, response=True)
            if uploadResponse.status_code == 200:
                imageID = json.loads(uploadResponse.content)['filename']
                break
            else:
                attempt += 1

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
        submitURL = postURL(getShowID(link), epID) + ('photos' if not epID else 'cover')
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
    except ConnectionRefusedError:
        print(f'Failed to post {file}')
        return False


def retrieveSummary(cookies, epID):
    summaryURL = postURL(epID=epID)
    response = g.soup(summaryURL, params=parameters(cookies, undef=True), cookies=cookies, JSON=True)['revision']
    return {'title': response['title'], 'summary': response['summary']}


## Updates the episode summary
# summary (str) : Summary of the episode
# notes (str) : Notes for reviewing staff to read
def summarySubmit(cookies, epID, summary='', title='', notes=''):
    if summary or title:
        dataForm = {
            'category': 'details',
            'notes': notes,
            'summary': summary,
            'title': title
        }
        submitURL = postURL(epID=epID) + 'details'
        response = g.soup(submitURL, data=dataForm, params=parameters(cookies, undef=True), cookies=cookies,
                          post=True, response=True)
        if response.status_code == 200:
            return True
        else:
            print(f'Failed to update {epID}')
            return False
    else:
        return False


def deleteSubmission(cookies, category, link=None, epID=None):
    if category:
        deleteURL = f"{siteRoot}/v1/edit/tickets/{epID}/episodes" \
            if epID else f"{siteRoot}/v1/edit/titles/{getShowID(link)}/titles"
        params = {
            'category': category
        }
        params.update(parameters(cookies, undef=True if epID else False))
        g.delete(deleteURL, params=params)
    else:
        raise SyntaxError


def dramaList(cookies, watching=True, completed=True, plan_to_watch=True, hold=True, drop=True, not_interested=True,
              suppress=False):
    profileLink = f"{siteRoot}/profile"
    listLink = f"{siteRoot}{g.soup(profileLink, cookies=cookies).find('a', text='My Watchlist')['href']}"
    listSoup = g.soup(listLink, cookies=cookies)
    myDramaList = {
        'watching': listSoup.find(id='list_1') if watching else None,
        'completed': listSoup.find(id='list_2') if completed else None,
        'plan_to_watch': listSoup.find(id='list_3') if plan_to_watch else None,
        'on_hold': listSoup.find(id='list_4') if hold else None,
        'dropped': listSoup.find(id='list_5') if drop else None,
        'not_interested': g.soup(f"{listLink}/not_interested", cookies=cookies).find(id='list_6')
        if not_interested else None
    }

    def userInfo(ID):
        infoSoup = g.soup(f"{siteRoot}/v1/users/watchaction/{ID}",
                          params=parameters(cookies),
                          cookies=cookies,
                          JSON=True)['data']
        return {
            'date-start': None if infoSoup['date_start'] == '0000-00-00'
            else d.datetime.strptime(infoSoup['date_start'], '%Y-%m-%d'),
            'date-end': None if infoSoup['date_finish'] == '0000-00-00'
            else d.datetime.strptime(infoSoup['date_finish'], '%Y-%m-%d'),
            'rewatched': infoSoup['times_rewatched']
        }

    for key in [i for i in myDramaList if myDramaList[i]]:
        try:
            myDramaList[key] = {
                int(show['id'][2:]): {
                    'title': show.find(class_='title').text,
                    'country': show.find(class_='sort2').text,
                    'year': int(show.find(class_='sort3').text),
                    'type': show.find(class_='sort4').text,
                    'rating': float(show.find(class_='score').text)
                    if show.find(class_='score') or float(show.find(class_='score').text) != 0.0 else None,
                    'progress': int(show.find(class_='episode-seen').text) if show.find(class_='episode-seen') else 0,
                    'total': int(show.find(class_='episode-total').text) if show.find(class_='episode-seen') else 0,
                } for show in myDramaList[key].tbody.find_all('tr')
            }
        except (AttributeError, KeyError):
            myDramaList[key] = None

    totalShows = len([i for j in myDramaList if myDramaList[j] for i in myDramaList[j]])
    k = 0
    for key in [i for i in myDramaList if myDramaList[i]]:
        for k, showID in enumerate(myDramaList[key], start=k + 1):
            myDramaList[key][showID].update(userInfo(showID))
            g.printProgressBar(k, totalShows, prefix=f'Retrieving {k}/{totalShows}') if not suppress else True
    return myDramaList


def updateExternalLinks(cookies, link, externalLinks, notes=''):
    if externalLinks:
        submitURL = postURL(showID=getShowID(link)) + 'details'
        params = parameters(cookies)
        # External links example
        # externalLinks = [
        #     {
        #         "key": "website",
        #         "label": "Official site (MBS)",
        #         "text": "",
        #         "type": "uri",
        #         "value": "https://www.mbs.jp/araoto_drama/",
        #         "_status": "created"
        #     },
        #     {
        #         "key": "twitter",
        #         "label": "",
        #         "text": "",
        #         "type": "social",
        #         "value": "araoto_drama",
        #         "_status": "created"
        #     },
        #     {
        #         "key": "instagram",
        #         "label": "",
        #         "text": "",
        #         "type": "social",
        #         "value": "araoto_drama",
        #         "_status": "created"
        #     }
        # ]
        dataForm = {
            'external_links': externalLinks,
            'category': 'external_links',
            'notes': notes
        }
        response = g.soup(submitURL, params=params, cookies=cookies, data=dataForm, post=True, response=True)
        return True if response.status_code == 200 else False
    else:
        return True

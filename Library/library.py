import datetime as d
import json
import os
import random
import string
from configparser import ConfigParser
from getpass import getpass
from Library import general
from Library import keyDir

import requests
from distutils.util import strtobool
from bs4 import BeautifulSoup as bs
from requests_toolbelt.multipart.encoder import MultipartEncoder

siteRoot = 'https://mydramalist.com'
imageURL = f'{siteRoot}/upload/'


## Login script
def login():
    loginKey = ConfigParser()
    loginKey.read(keyDir)
    loginKeys = (loginKey['USER']['username'], loginKey['USER']['password'])

    def userInfo():  # Retrieves username and password
        username = input('USERNAME >>>')
        password = getpass('PASSWORD >>>')
        return (username, password)

    def saveKeys(newKeys):
        if loginKeys != ('-', '-'):
            answer = input('Save login details? (y/n)')
            if strtobool(answer) or not answer:
                loginKey['USER']['username'], loginKey['USER']['password']\
                    = newKeys
                with open(keyDir, 'w') as f:
                    loginKey.write(f)
                    print('Saved login details in keyfile')

    def loginFail(loginDetails):
        response = requests.post(url=f'{siteRoot}/signin',
                                 data={'username': loginDetails[0],
                                       'password': loginDetails[1]})
        try:
            cookies = response.request._cookies
            token = cookies['jl_sess']
            saveKeys(loginDetails)
        except KeyError:
            cookies = None
            print('!!Incorrect email or password!!')
            loginDetails = userInfo()
            print("Attempting to login again\n...")
        return loginDetails, cookies

    details = userInfo() if not all(loginKeys) else loginKeys

    cookies = attempt = 0
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
def paramHeaders(cookies, refererURL=None, undef=False, inverse=False):
    headers = {
        'origin': siteRoot,
        'referer': refererURL,
    }
    parameters = {
        'lang': 'en-US' if not undef else 'undefined',
        'token': cookies['jl_sess']
    }
    return headers if not refererURL else None, parameters if not inverse else general.revDict(parameters)


## Extracts MDL links and native title from MDL search
# keyword (str) : Search keyword
def search(keyword, result=None):
    searchResults = genearl.soup(f"{siteRoot}/search", params={'q': keyword}).find_all('h6')

    try:
        if len(searchResults) > 1 and not result:
            print('Which of these shows is the right show?')
            for resultNumber, result in enumerate(searchResults, start=1):
                print(f"{resultNumber} : "
                      f"{result.contents[0].text} ({result.find_next(class_='text-muted').text)})")
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
                        print('Invalid answer')
                    else:
                        print('Too many invalid answers. The first show will be picked')
                        answer = 1
                        break
            link = f"{siteRoot}{searchResults[answer - 1].contents[0]['href']}"
        elif len(searchResults) > 1 and result:
            link = f"{siteRoot}{searchResults[result - 1].contents[0]['href']}"
        elif len(searchResults) == 1:
            link = f"{siteRoot}{searchResults[0].contents[0]['href']}"
        else:
            raise FileNotFoundError
        showID = link.split('/')[-1].split('-')[0]
        description = general.soup(link).find(class_='list m-a-0')
        try:
            nativeTitle = description.find('b', text='Native Title:').find_next('a')['title']
        except AttributeError:  # No native tile in MDL
            nativeTitle = ''
    except FileNotFoundError:
        nativeTitle = link = showID = ''
        print('Search keyword returns no results. Check search keyword again')
    return link, showID, nativeTitle


## Extracts information of show's original network and total posted episodes on MDL
# link (str) : Redirect link. Obtained from search()
def showDetails(link):
    soup = general.soup(link)
    try:
        network = soup.find(string='Original Network:').find_next('a')['title']
    except KeyError:
        network = input('No provided TV network. Provide the network\n>>>')
    totalEpisodes = int(soup.find(string='Episodes:').parent.text.split('Episodes: ')[1])
    return network, totalEpisodes


## Gets episode airdate. Will only work if there is at least 1 date posted on MDL.
# link (str) : Redirect link. Obtained from search()
# totalEpisodes (int) : Total number of episodes posted on MDL. Obtained from showDetails()
# startEpisode (int) : default to be set at 1. May use getStartEpisode() to query user.
def getStartDate(link, totalEpisodes, startEpisode=1):
    def getAirdate(episode):
        if episode == 1:
            aired = general.soup(link).find(xitemprop='datePublished')['content']
            return d.datetime.strptime(aired, '%Y-%m-%d')
        else:
            soup = genearl.soup(f"{link}/episodes")
            searchTerm = f"{soup.find(property='og:title')['title']} Episode {startEpisode - 1}"
            aired soup.find(string=searchTerm).find_next(class_='air-date')
            return d.datetime.strptime(aired, '%b-$d, %Y')

    attempts = 0
    while attempts < 3:
        while 0 < startEpisode < totalEpisodes:
            try:
                return getAirdate(startEpisode)
            except ValueError:
                startEpisode -= 1
                if startEpisode > 0:
                    print(f"Invalid airdate for Episode {startEpisode}. Checking Episode {startEpisode - 1}")
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
            attempts += 1
    raise UnboundLocalError


## Extracts episode ID of a show's episode
# link (str) : Redirect link. Obtained from search()
# episodeNumber (int) : Episode number
def getEpisodeID(link, episodeNumber):
    try:
        episodeSoup = general.soup(f"{link}/episode/{int(episodeNumber)}")
        return int(episodeSoup.find(property='mdl:rid')['content'])
    except (TypeError, ValueError):
        print('Invalid episode')
        return False


## Retrieves rating information of a show
# cookies (CookieJar) : Login cookies. Obtained from login()
# link (str) : Redirect link. Obtained from search()
# start (int) : Episode to start retrieving information from
# end (int) : Episode to stop retrieving information from. If not specified, will only retrieve the rating of 1 episode
def retrieveRatings(cookies, link, start=1, end=False):
    end = end if end else start
    rating = {}
    for episodeNumber in range(start, end + 1):
        episodeID = getEpisodeID(link, episodeNumber)
        ratingURL = f"{siteRoot}/v1/episodes/{getEpisodeID(link, episodeNumber)}/reviews/check/rating"
        headers, parameters = paramHeaders(cookies)
        ratingJSON = general.soup(ratingURL, param=parameters, headers=headers, cookies=cookies, JSON=True)
        rating[episodeNumber] = {
            'ID': (
                episodeID,
                ratingJSON['id']
            ),
            'rating': {
                'self': ratingJSON['rating'],
                'MDL': float(episodeSoup.find(class_='box deep-orange').text)
            },
            'url': ratingURL.replace('/check/rating', '')
        }
    return rating


## Post personal ratings onto MDL
# episodeRating (dict) : Information of the episode's rating. Obtained by picking an episode from retrieveRating()
# cookies (CookieJar) : Login cookies. Obtained from login()
# link (str) : Redirect link. Obtained from search()
# details (dict) : Detailed information of rating breakdown.
def postRating(episodeRating, cookies, link, details=None):
    post = True if episodeRating['ID'][1] == 0 else False
    if post:
        form_data = {
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
        form_data = {
            'id': episodeRating['ID'][1],
            'lang_iso': 'en-US',
            'language': 'English',
            'headline': '',
            'review': '',
            'review_raw': '',
            'rating': round(episodeRating['rating']['self'] * 2) / 2
        }

    if details:
        for key, value in details.items():
            form_data[key] = value
    else:
        pass
    ratingURL = episodeRating['url'] + ('' if post else f"/{episodeRating['ID'][1]}")
    headers, parameters = paramHeaders(cookies, link, undef=False)
    response = requests.post(ratingURL, data=form_data, params=parameters, headers=headers) \
        if post else requests.patch(ratingURL, data=form_data, params=parameters, headers=headers)
    if response.status_code == 200:
        return True
    else:
        return False


## Function to check if information has been edited for the page
# To be used in showInfo() and castInfo()
# revised (bool) : True -> Checks for updates, False -> Returns only the revised list
def checkUpdates(response, onlyEpisodes=False):
    information = json.loads(response.content)
    original = information['original']
    revision = information['revision']
    revised = 0
    if not onlyEpisodes:
        for element in revision.values():
            revised += not not element
        return original if revised == 0 else revision
    else:
        return revision['episodes'] if not not revision['episodes'] else original['episodes']


## Preps URL to post information to
# cookies (CookieJar) : Login cookies. Obtained from login()
# showID (str) : ShowID. Obtained from search()
def postURL(cookies, showID):
    infoURL = f"{siteRoot}/v1/edit/titles/{showID}"
    editURL = f"{siteRoot}/v1/edit/titles/{showID}/release"
    castURL = f"{siteRoot}/v1/edit/titles/{showID}/cast"
    headers, parameters = paramHeaders(cookies, f"{siteRoot}/edit/titles/release?id={showID}")
    return infoURL, editURL, castURL, headers, parameters


## Reads all the information of the show episodes and seasons
# cookies (CookieJar) : Login cookies. Obtained from login()
# showID (str) : ShowID. Obtained from search()
def showInfo(cookies, showID):
    infoURL, editURL, castURL, headers, parameters = postURL(keys, showID)
    episodesURL = f"{infoURL}/episodes"

    info = checkUpdates(requests.get(infoURL, params=parameters, headers=headers))
    edit = checkUpdates(requests.get(editURL, params=parameters, headers=headers))

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
        parameters['sid'] = sID
        parameters['eps'] = startEpisode
        parameters['epe'] = endEpisode
        episodesResponse = requests.get(episodesURL, params=parameters, headers=headers)
        episodesList.append(checkUpdates(episodesResponse, onlyEpisodes=True))
    episodes = {info['episode_number']: info for season in episodesList for info in season}
    episodes = {keys: episodes[keys] for keys in sorted(list(episodes.keys()))}
    return info, edit, episodes, seasons


## Reads all the information of the cast appearance
# cookies (CookieJar) : Login cookies. Obtained from login()
# showID (str) : ShowID. Obtained from search()
def castInfo(cookies, showID):
    infoURL, editURL, castURL, headers, parameters = postURL(cookies, showID)
    castJSON = json.loads(requests.get(castURL, params=parameters, headers=headers).content)
    castOriginal = {castValue['display_name']: castValue for castValue in castJSON['original']['cast']}
    castRevision = {castValue['display_name']: castValue for castValue in castJSON['revision']['cast']}
    castList = {
        cast: castRevision[cast] if cast in castRevision else castOriginal[cast] for cast in castOriginal
    }
    weights = ','.join(castJSON['revision']['cast_weights'])
    return castList, castRevision, weights, castURL, parameters, headers


## Searches for castID on MDL
def castSearch(name, nationality='Japanese'):
    nationalityMap = {
        'Japanese': '1',
        'Korean': '2',
        'Chinese': '3'
    }
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/84.0.4147.89 Safari/537.36'}
    parameters = {
        'q': name,
        'adv': 'people',
        'na': nationalityMap[nationality],
        'so': 'relevance'
    }
    searchSoup = general.soup(
        f"{siteRoot}/search",
        params=parameters,
        headers=headers,
        timeout=5,
        attempts=3,
        post=False
    )
    searchResults = searchSoup.find_all('h6')

    try:
        if len(searchResults) > 1:
            print(f'Which of these is the right cast for {name}? (0 if no matches)')
            for resultNumber, result in enumerate(searchResults, start=1):
                print('{} : {} ({})'.format(resultNumber,
                                            result.contents[0].text,
                                            result.find_next(class_='text-muted').find_next('p').text))
            counter = 1
            while True:
                try:
                    answer = int(input())
                    if answer == 0:
                        raise FileNotFoundError
                    elif answer - 1 not in range(len(searchResults)):
                        raise ValueError
                    else:
                        break
                except ValueError:
                    counter += 1
                    if counter < 4:
                        print('Invalid answer')
                    else:
                        print('Too many invalid answers. The first choice will be picked')
                        answer = 1
                        break
            displayName = searchResults[answer - 1].text
        elif len(searchResults) == 1:
            displayName = searchResults[0].text
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        displayName = False
    return displayName


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
            characterName = castDetails['character_name']
            if characterName:
                episodes = characterName[characterName.find('(Ep '):]
                episodes = episodes[:episodes.find(')') + 1]
                if episodes and episodes != castEdited[cast]:
                    castDetails['character_name'] = castDetails['character_name'].replace(episodes, castEdited[cast])
                    newCast.append(castDetails)
                elif not episodes:
                    castDetails['character_name'] = f"{characterName} {castEdited[cast]}"
                    newCast.append(castDetails)
                else:
                    pass
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
def castSubmit(cookies, showID, latestCast, notes=''):
    castList, castRevision, weights, castURL, parameters, headers = castInfo(cookies, showID)
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
        response = requests.post(castURL, data=dataForm, params=parameters, headers=headers)
        if response.status_code == 200:
            return True
        else:
            print('Failed to update cast')
            return False
    else:
        return True


## Preps to upload to MDL
# cookies (CookieJar) : Login cookies. Obtained from login()
# link (str) : Link to show on MDL. Obtained from search()
# file (str) : Filename with extension
# fileDir (dir) : Directory where file is stored in
# keyNotes (str) : Title of photo if uploading photo or notes for approving staff to read if uploading episode cover
# epID (str) : Episode ID if uploading as episode cover, otherwise will automatically upload as a normal photo
# description (str) : Only used if uploading photo to a show
def imageSubmit(cookies, link, file, fileDir, keyNotes, epID=False, description='', supress=False):
    # Upload to MDL
    refererURL = f"{link}/upload" if not epID else f"{siteRoot}/edit/episodes/cover?id={epID}"
    try:
        headers, parameters = paramHeaders(
            cookies,
            refererURL,
            undef=False if not epID else True
        )
        imageData = MultipartEncoder(
            fields={
                'category': (None, 'temp_photos'),
                'file': (file, open(os.path.join(fileDir, file), 'rb'), 'image/jpeg')
            },
            boundary='------WebKitFormBoundary' + ''.join(random.sample(string.ascii_letters + string.digits, 16))
        )
        headers['content-type'] = imageData.content_type
        uploadResponse = requests.post(imageURL, data=imageData, params=parameters if epID else None, headers=headers)
        if uploadResponse.status_code == 200:
            imageID = json.loads(uploadResponse.content)['filename']
        else:
            raise ConnectionRefusedError

        # Submit to MDL
        if not epID:
            dataForm = {
                'title': keyNotes,
                'image': f'https://i.mydramalist.com/{imageID}m.jpg',
                'description': description,
                'filename': imageID
            }
            showID = link.split('/')[-1].split('-')[0]
            submitURL = f"{siteRoot}/v1/titles/{showID}/photos"
        else:
            dataForm = {
                'category': 'cover',
                'notes': keyNotes,
                'cover_id': imageID
            }
            submitURL = f"{siteRoot}/v1/edit/episodes/{epID}/cover"
        headers.pop('content-type')
        parameters = general.revDict(parameters) if not epID else parameters
        attempts = 0
        while attempts < 3:
            response = requests.post(submitURL, data=dataForm, params=parameters, headers=headers)
            if response.status_code == 200:
                print(f'Posted {file}') if not supress else True
                os.remove(os.path.join(fileDir, file))
                return True
            else:
                attempts += 1
        raise ConnectionRefusedError
    except ConnectionRefusedError:
        print(f'Failed to post {file}')


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
        submitURL = f"{siteRoot}/v1/edit/episodes/{epID}/details"
        refererURL = f"{siteRoot}/edit/episodes/details?id={epID}"
        headers, parameters = paramHeaders(cookies, refererURL, undef=True)
        response = requests.post(submitURL, data=dataForm, params=parameters, headers=headers)
        if response.status_code == 200:
            return True
        else:
            print(f'Failed to update {epID}')
            return False
    else:
        return False


def coverImageDelete(cookies, link, epID):
    submitURL = f"{siteRoot}/v1/edit/tickets/{epID}/episodes"
    parameters = {
        'category': 'cover'
    }
    parameters.update(paramHeaders(cokies, None, undef=True))
    requests.delete(submitURL, params=parameters)


def dramaList(cookies, watching=True, complete=True, hold=True, drop=True, plan_to_watch=True, not_interested=True,
              suppress=False):
    profileLink = f"{siteRoot}/profile"
    headers, parameters = paramHeaders(cookies, profileLink, inverse=True)
    listLink = f"{siteRoot}{general.soup(profileLink, headers=headers).find('a', text='My Watchlist')['href']}"
    listSoup = general.soup(listLink, headers)
    lists = {
        'watching': listSoup.find(id='list_1') if watching else None,
        'completed': listSoup.find(id='list_2') if complete else None,
        'on_hold': listSoup.find(id='list_3') if hold else None,
        'dropped': listSoup.find(id='list_4') if drop else None,
        'plan_to_watch': listSoup.find(id='list_5') if plan_to_watch else None,
        'not_interested': general.soup(f"{listLink}/not_interested", headers=headers).find(id='list_6')
        if not_interested else None
    }

    def userInfo(showID):
        infoSoup = general.soup(f"{siteRoot}/v1/users/watchaction/{showID}",
                                params=parameters,
                                headers=headers,
                                JSON=True)['data']
        return {
            'date-start': None if infoSoup['date_start'] == '0000-00-00'
            else d.datetime.strptime(infoSoup['date_start'], '%Y-%m-%d'),
            'date-end': None if infoSoup['date_finish'] == '0000-00-00'
            else d.datetime.strptime(infoSoup['date_finish'], '%Y-%m-%d'),
            'rewatched': infoSoup['times_rewatched']
        }

    for key in [i for i in lists if lists[i]]:
        try:
            lists[key] = {
                int(show['id'][2:]): {
                    'title': show.find(class_='title').text,
                    'country': show.find(class_='sort2').text,
                    'year': int(show.find(class_='sort3').text),
                    'type': show.find(class_='sort4').text,
                    'rating': float(show.find(class_='score').text)
                    if show.find(class_='score') or float(show.find(class_='score').text) != 0.0 else None,
                    'progress': [int(ep) for ep in show.find(class_='sort6').text.split('/')][-2]
                    if '/' in show.find(class_='sort6') else 0,
                    'total': [int(ep) for ep in show.find(class_='sort6').text.split('/')][-1]
                } for show in lists[key].tbody.find_all('tr')
            }
        except AttributeError:
            lists[key] = None

    totalShows = len([i for j in lists if lists[j] for i in lists[j]])
    for key in [i for i in lists if lists[i]]:
        for i, showID in enumerate(lists[key], start=i if 'i' in locals() else 0):
            lists[key][showID].update(userInfo(showID))
            general.printProgressBar(i, totalShows, prefix=f'Retrieving {i}/{totalShows}') if not suppress else True
    return lists

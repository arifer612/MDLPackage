import datetime as d
import json
import re
from mdl.Library import general as g

programRoot = 'https://www.tv-tokyo.co.jp/broad_bstvtokyo/program/'


## Search for show, allows user to pick from choice of 16 results
def search(title):
    searchPayload = {
        "siteIds": ["1131766696319858895", "1132892598783763540"],
        "count": 16,  # Change this where appropriate
        "query": "query(\"{}\")".format(title),
        "logQuery": "{}".format(title),
        "filter": "filter(txn-program-top:\"true\")AND NOT ( filter(txn-search-exclusion:\"true\") )",
        "sort": [{"type": "score", "order": "descending"}],
        "start": 0
    }
    searchParams = {
        'persisted': '7d761bd0a4b2aea78276c7e6b0e9b3231f962652',
        'json': json.dumps(searchPayload, ensure_ascii=False).encode('utf8')
    }
    searchURL = 'https://api.cxense.com/document/search?'
    searchResults = g.soup(searchURL, params=searchParams, JSON=True)
    if searchResults['totalCount'] == 1:
        return {entry['field']: entry['value'] for entry in searchResults['matches'][0]['fields']}
    elif searchResults['totalCount'] > 1:
        print('Which of the following is the right show:')
        for resultNum, result in enumerate(searchResults['matches'], 1):
            showInfo = {entry['field']: entry['value'] for entry in result['fields']}
            query = f"{resultNum}: Title -- {showInfo['title']}"
            if 'txn-broadcast-time' in showInfo.keys():
                if '曜' in showInfo['txn-broadcast-time']:
                    query += f" airing on {showInfo['txn-broadcast-time']}"
                else:
                    query += f", {showInfo['txn-broadcast-time']}"
            else:
                pass
            print(query)

        answer = attempt = 0
        while answer not in range(1, searchResults['totalCount'] + 1) and attempt < 4:
            try:
                answer = int(input()) if attempt == 0 else int(input('Invalid choice. Pick again'))
            except ValueError:
                pass
            attempt += 1
            if attempt < 3:
                pass
            else:
                print('Too many invalid attempts. Picking the first choice')
                answer = 1

        return {entry['field']: entry['value'] for entry in searchResults['matches'][answer - 1]['fields']}
    else:
        raise FileNotFoundError


def getPageID(showInfo):
    return f"pg_{str(showInfo['txn-program-id']).zfill(10)}.json"


## Scrapes internal database for information on show
def getData(title, fixed=False):
    showInfo = search(title)
    pageID = getPageID(showInfo)
    BS = 'ＢＳ' in showInfo['txn-broadcaster']
    dataFull = g.soup(f"{programRoot.replace('bs', '' if not BS else 'bs')}data/{pageID}", JSON=True)
    dataEpisodes = {int(year[:4]): payload for year, payload in dataFull['backnumber']['data'].items()}
    showTitle = dataFull['bangumi'] if not fixed else title
    return dataEpisodes, showTitle, BS


## Analyses episode data for air dates
# data (dict) : Retrieved from getData()
# showTitle (str) : Retrieved from getData()
# BS (bool) : True for bsTokyo shows
def getEpisodeDates(data, showTitle=None, BS=False):
    datetimeInfo = re.split('[_.]', data['url'])[1]
    try:
        startTime = d.datetime.strptime(datetimeInfo, '%Y%m%d%H%M')
    except ValueError:
        datetimeInfo = str(int(datetimeInfo) - 2400)
        startTime = d.datetime.strptime(datetimeInfo, '%Y%m%d%H%M') + d.timedelta(days=1)
    episodeTitle = data['txt'].replace(showTitle if showTitle else '', '')
    episodeURL = f"{programRoot.replace('bs', '' if not BS else 'bs')}detail/{data['url']}"
    if startTime < d.datetime.now():
        return {'start': startTime,
                'title': episodeTitle,
                'url': episodeURL}
    else:
        return False


## Compact function to scrape for episodes
# title (str) : Title
# start (int) : Episode to begin truncation
# initialValue (int) : Value of first episode, ONLY change this if the show does not start at #1
def showDates(title, start=0, fixed=False, initialValue=1):
    dataEpisodes, showTitle, BS = getData(title, fixed)
    totalEpisodes = initialValue
    episodeList = {}
    seasons = {}
    for year in sorted(dataEpisodes):
        episodeList.update({episodeNumber: getEpisodeDates(info, showTitle, BS)
                            for episodeNumber, info in enumerate(dataEpisodes[year], start=totalEpisodes)
                            if (episodeNumber > start)})
        seasons[year] = {'start': totalEpisodes,
                         'end': totalEpisodes + len(dataEpisodes[year]) - 1,
                         'startDate': episodeList[totalEpisodes]['start']
                         }
        totalEpisodes += len(dataEpisodes[year])

    [episodeList.pop(i, None) for i in [j for j in episodeList if not episodeList[j]]]
    return episodeList, seasons


## Preps information to be posted to MDL
# episodes (dict) : Highly suggest to include all the episodes at once, rather than to split by season
# airTime (str) : To be obtained from MDL, in HHMM format
def formData(episodes, airTime):
    airTime = str((int(airTime) - 900) % 2400).zfill(4)
    payload = [
        {
            "episode_number": episode,
            "release_date": d.datetime.strftime(date['start'] - d.timedelta(hours=9), '%Y-%m-%d'),
            "release_time": d.datetime.strftime(date['start'] - d.timedelta(hours=9, minutes=date['start'].minute % 5),
                                                '%H:%M'),
            "released_at": d.datetime.strftime(date['start'] - d.timedelta(hours=9, minutes=date['start'].minute % 5),
                                               '%Y-%m-%d %H:%M:00'),
            "status": "auto"
        }
        for episode, date in episodes.items()
    ]
    [episode.update({'status': 'updated', 'delay_reason': 1}) for episode in payload
     if episode['release_time'].replace(':', '') != airTime]
    return payload


def episodeImages(title, episodeStart=1, fixed=False):
    dataEpisodes, showTitle, BS = getData(title, fixed=fixed)
    return {
        epNum: {
            'url': f"{programRoot.replace('bs', '' if not BS else 'bs')}detail/{epDetails['url']}",
            'airDate': d.datetime.strptime(re.split('[_.]', epDetails['url'])[1], '%Y%m%d%H%M')
            if int(re.split('[_.]', epDetails['url'])[1][-4:]) < 2400 else
            d.datetime.strptime(str(int(re.split('[_.]', epDetails['url'])[1]) - 2400), '%Y%m%d%H%M'),
            'txt': epDetails['txt'],
            'keyNotes': f"TvTokyo Gallery Episode {epNum} ",
            'description': '',
            'images': [f"https:{image['href']}"
                       for gallery in g.soup(f"{programRoot}detail/{epDetails['url']}")
                           .find_all(class_='tbcms_program-gallery__list')
                       for image in gallery.find_all(href=True)]
        } for year, yearList in dataEpisodes.items()
        for epNum, epDetails in enumerate(yearList, start=1)
        if epNum >= episodeStart
    }

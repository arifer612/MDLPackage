import datetime as d
import json
import requests
from Library import general as g

programRoot = 'https://www.tv-tokyo.co.jp/broad_bstvtokyo/program/data/'


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
    searchResponse = requests.get(searchURL, params=searchParams)
    searchResults = json.loads(searchResponse.content)
    if searchResults['totalCount'] > 1:
        print('Which of the following is the right show:')
        for resultNum, result in enumerate(searchResults['matches'], 1):
            showInfo = {entry['field']: entry['value'] for entry in result['fields']}
            query = f"{resultNum}: Title -- {showInfo['title']}"
            if 'txn-broadcast-time' in showInfo.keys():
                query += f" airing on {showInfo['txn-broadcast-time']}"
            else:
                pass
            print(query)
        answer = input()
        showInfo = {entry['field']: entry['value']
                    for entry in searchResults['matches'][int(answer) - 1]['fields']}
    elif searchResults['totalCount'] == 1:
        showInfo = {entry['field']: entry['value']
                    for entry in searchResults['matches'][0]['fields']}
    else:
        showInfo = None
        exit('Invalid search terms')
    return showInfo


## Extracts timetable URL of the show instead of show's official site
def URL(title):
    showInfo = search(title)
    BS = 'ＢＳ' in showInfo['txn-broadcaster']
    jpConvert = {'月': 1, '火': 2, '水': 3, '木': 4, '金': 5, '土': 6, '日': 7}
    [airDay, airtime] = showInfo['txn-broadcast-time'].split('夜')
    airDay = jpConvert[airDay[0]]
    try:
        airtime = d.datetime.strptime(airtime, '%H時%M分')
    except ValueError:
        airtime = d.datetime.strptime(airtime, '%H時')
    HRS = f"{str(airtime.hour + (24 if airtime.hour < 4 else 12)).zfill(2)}{str(airtime.minute).zfill(2)}"
    today = d.datetime.now().weekday() + 1
    timeDelta = (today - airDay) % 7
    searchDate = d.datetime.strftime(d.datetime.now() - d.timedelta(days=timeDelta), '%Y%m%d')
    timetableResponse = requests.get(f'https://www.tv-tokyo.co.jp/tbcms/assets/data/{searchDate}.json')
    if timetableResponse.status_code == 200:
        timetable = json.loads(timetableResponse.content)
        showURL = f"https:{timetable[HRS][str(BS + 1)]['url']}"
    else:
        showURL = None
        exit('Fail to retrieve timetable information')
    return showURL, d.datetime.strftime(airtime, '%H:%M'), BS  # airTime needed to check against past airtime


## Internal ID tag employed by TV Tokyo to identify shows
def getID(showURL):
    return g.soup(showURL, post=False).find(class_='tbcms_contents')['data-program'].split('/')[-1]


## Scrapes internal database for information on show
def getData(title, fixed=False):
    showURL, airTime, BS = URL(title)
    showID = getID(showURL)
    dataFull = g.soup(f"https://www.tv-tokyo.co.jp/broad_{'bs' if BS else ''}tvtokyo/program/data/{showID}", JSON=True)
    dataEpisodes = {int(year[:4]): payload for year, payload in dataFull['backnumber']['data'].items()}
    showTitle = dataFull['bangumi'] if not fixed else title
    # variety = 'バラエティ・音楽' in dataFull['genre'] ## boolean. Checks if the show is a variety show
    return dataEpisodes, showTitle, showURL, airTime, BS


## Extracts exact airdate and airtime of show in JST
# data (dict) : needs keys 'url' and 'txt'
# showTitle (str) : used for getting episodeTitle
# BS (bool) : True for bsTokyo shows
def analyse(data, showTitle=None, BS=False):
    datetimeInfo = data['url'].split('_')[1].split('.')[0]
    try:
        startTime = d.datetime.strptime(datetimeInfo, '%Y%m%d%H%M')
    except ValueError:
        datetimeInfo = str(int(datetimeInfo) - 2400)
        startTime = d.datetime.strptime(datetimeInfo, '%Y%m%d%H%M') + d.timedelta(days=1)
    episodeTitle = data['txt'].replace(showTitle if showTitle else '', '')
    episodeURL = f"https://www.tv-tokyo.co.jp/broad_{'bs' if BS else ''}tvtokyo/program/detail/{data['url']}"
    if startTime < d.datetime.now():
        return {'start': startTime - d.timedelta(minutes=startTime.minute % 5),
                'title': episodeTitle,
                'url': episodeURL}
    else:
        return False


## Compact function to scrape for episodes
# auto (bool) : splits season by year. Recommended for variety shows / music shows etc.
# start (int) : episode number to start working from
# initialValue (int) : value of first episode, only change this if the show does not start at #1
def showDates(title, start=0, initialValue=1, fixed=False):  # initialValue=0 # start: value of first episode
    dataEpisodes, showTitle, showURL, airTime, BS = getData(title, fixed)
    totalEpisodes = initialValue
    episodeList = {}
    seasons = {}
    for year in sorted(dataEpisodes):
        seasons[year] = {'start': totalEpisodes,
                         'end': totalEpisodes + len(dataEpisodes[year]) - 1,
                         'startDate': d.datetime.strptime(dataEpisodes[year][0]['url'].split('_')[1].split('.')[0],
                                                          '%Y%m%d%H%M')
                         }
        episodeList.update({episodeNumber: analyse(info, showTitle, BS)
                            for episodeNumber, info in enumerate(dataEpisodes[year], start=totalEpisodes)
                            if (episodeNumber > start) and analyse(info, showTitle, BS)})
        totalEpisodes += len(dataEpisodes[year])
    return episodeList, seasons, airTime


## Preps information to be posted to MDL
# seasonEpisodes (dict) : Highly suggest to include all the episodes at once, rather than to split by season
def formData(seasonEpisodes, airTime):
    payload = [
        {
            "episode_number": episode,
            "release_date": d.datetime.strftime(date['start'] - d.timedelta(hours=9), '%Y-%m-%d'),
            "release_time": d.datetime.strftime(date['start'] - d.timedelta(hours=9), '%H:%M'),
            "released_at": d.datetime.strftime(date['start'] - d.timedelta(hours=9), '%Y-%m-%d %H:%M:00'),
            "status": "auto",
        }
        for episode, date in seasonEpisodes.items()
    ]
    for episode in payload:
        if d.datetime.strftime(d.datetime.strptime(airTime, '%H:%M') - d.timedelta(hours=9), '%H:%M:00') \
                != episode['released_at'].split(' ')[1]:
            episode['status'] = 'updated'
            episode['delay_reason'] = 1
    return payload


# episodes, total, airtime = showDates('YOUは何しに日本へ')

# Specific script to check airdates for past episodes of もっと！もっと！YOUは何しに日本へ？Z
def supercharged(title='もっと！もっと！YOUは何しに日本へ？Z', oldID=24922, startDate=d.datetime(2018, 4, 3, 21, 00), maxWeeks=52):
    showURL, airTime, BS = URL(title)

    def checkURL(date, oldID):
        url = 'https://www.tv-tokyo.co.jp/broad_bstvtokyo/program/detail/{}/{}_{}.html'.format(
            d.datetime.strftime(date, '%Y%m'),
            oldID,
            d.datetime.strftime(date, '%Y%m%d%H%M')
        )
        return url if BS else url.replace('bs', '')

    pastEpisodes = {}
    counter = 0
    for weeks in range(maxWeeks):
        date = startDate + d.timedelta(weeks=weeks)
        try:
            showID = getID(checkURL(date, oldID))
            checkResponse = requests.get('https://www.tv-tokyo.co.jp/broad_bstvtokyo/program/data/{}'.format(
                showID).replace('bs', '' if not BS else 'bs'),
                                         headers={'referer': checkURL(date, oldID)})
            showTitle = json.loads(checkResponse.content)['bangumi']
            if showTitle == 'もっと！もっと！YOUは何しに日本へ？Z':
                counter += 1
                pastEpisodes[counter] = analyse({'url': checkURL(date, oldID).split('detail/')[1],
                                                 'txt': showTitle},
                                                BS=True)
            print('{} : {}'.format(d.datetime.strftime(date, '%Y%m%d'), showTitle))
        except Exception:
            print('{} : NONE'.format(d.datetime.strftime(date, '%Y%m%d')))
            pass
    print('Finished')
    pastSeasons = {
        str((list(pastEpisodes.values())[0]['start']).year):
            [list(pastEpisodes.keys())[0],
             list(pastEpisodes.keys())[-1],
             list(pastEpisodes.values())[0]['start']]
    }
    return pastEpisodes, pastSeasons


def episodeImages(title, episodeStart=1):
    dataEpisodes, showTitle, showLink, airtime, BS = getData(title)
    return {
        epNum: {
            'url': f"{'/'.join(showLink.split('/')[:-2])}/{epDetails['url']}",
            'airdate': d.datetime.strptime(f"{year} {epDetails['day']}", '%Y %m月%d日'),
            'txt': epDetails['txt'],
            'keyNotes': f"TvTokyo Gallery Episode {epNum} ",
            'description': '',
            'images': [f"https:{image['href']}"
                       for image in g.soup(f"{'/'.join(showLink.split('/')[:-2])}/{epDetails['url']}")
                                   .find(class_='tbcms_program-gallery__list').find_all(href=True)]
        } for year, yearList in dataEpisodes.items()
        for epNum, epDetails in enumerate(yearList, start=1)
        if epNum >= episodeStart
    }

## Datazoo searches episodes backwards from the latest episode to the first and has a database that starts on
#   2010/04/15. I recommend using this over kakaku especially if the show begins after 2010 as kakaku usually has very
#   messy cast information.

## Kakaku searches episodes forward in time from the first episode to the last. This should be used as a backup option
#   for it has a very messy database for some variety shows.

import datetime as d
from Library import general as g
from bs4 import BeautifulSoup as bs
import json
import re

rootZoo = 'https://datazoo.jp'
rootKakaku = 'https://kakaku.com'
networkDictionary = {'NTV': 4, 'TV Asahi': 10, 'TBS': 6, 'TV Tokyo': 12, 'Fuji TV': 8}


# nativeTitle (str) : Japanese title, needs not be exact but preferable
# airDate (str) : Last aired date in YYYY/MM/DD format if searching by title, else in datetime (Y, m, d, H, M) format
def searchDataZoo(nativeTitle, airDate=None, exclusions='', totalResults=1):
    if type(totalResults) != int:
        print('totalResults only accepts integer values')
        raise TypeError
    if type(airDate) == d.datetime:
        if airDate >= d.datetime(2010, 4, 15):
            queryURL = f"{rootZoo}/d/{airDate.year}/{airDate.month}/{airDate.day}/{int(airDate.hour / 6) + 1}"
            soup = g.soup(queryURL)
            link = f"{rootZoo}{soup.find(string=nativeTitle).parent['href']}"
            return link, airDate
        else:
            print('Too far back in time, not within database')
    elif type(airDate) == str:
        queryURL = 'https://cse.google.com/cse/element/v1'
        params = {
            'rsz': 'filtered_cse',
            'num': totalResults,
            'hl': 'ja',
            'source': 'gcsc',
            'gss': '.com',
            'cselibv': '26b8d00a7c7a0812',
            'cx': 'partner-pub-1955300006877540:6422076301',
            'q': f"{nativeTitle} {airDate} -{exclusions}",
            'safe': 'active',
            'cse_tok': 'AJvRUv29OfLq77RISJdH3hnYlRBU:1599371773557',
            'exp': 'csqr.cc',
            'oq': f"{nativeTitle} {airDate}",
            'gs_I': 'partner-generic.3...10019.11097.2.11305.0.0.0.0.0.0.0.0..0.0.csems,nrl=13...0.11073j100193469j5j2...'
                    '1.34.partner-generic..0.0.0.',
            'callback': 'google.search.cse.api16222'
        }
        headers = {'user-agent': 'Mozilla/5.0'}
        try:
            response = g.soup(queryURL, params=params, headers=headers, response=True)
            if response.status_code == 200:
                result = [i for i in json.loads(response.content[35:-2])['results'] if '/tv/' in i['url']]
                if len(result) == 0:
                    raise FileNotFoundError
                elif len(result) == 1:
                    result = result[0]
                else:
                    print('Which of the following is the right result?')
                    for i, r in enumerate(result, start=1):
                        print(f"{i} : {r['richSnippet']['metatags']['title']}")
                    answer = attempt = 0
                    while attempt < 3:
                        try:
                            answer = int(input('Result No.')) if attempt == 0 else int(input('Invalid answer. Result No.'))
                            if answer not in range(1, totalResults + 1):
                                raise ValueError
                            else:
                                break
                        except ValueError:
                            attempt += 1
                            if attempt < 3:
                                pass
                            else:
                                print('Too many invalid attempts. Picking first choice')
                                answer = 1
                                break
                    result = result[answer - 1]
                title = result['richSnippet']['metatags']['title']
                title = g.japaneseDays(title[:title.find(' の放送内容')][-18:], ['(', ')'])
                return result['url'], d.datetime.strptime(title, '%Y/%m/%d%a%H:%M')
            else:
                raise FileNotFoundError
        except (FileNotFoundError, KeyError):
            print('No search results')
            return False, False


def dataZoo(link):
    soup = g.soup(link)
    information = {
        'cast': [name.split('（')[0]
                   for name in soup.find(class_='icn_cast').next_sibling.text.replace('\n', '').split('\xa0')],
        'url': link
    }
    try:
        history = soup.find(class_='oldprogram').find_all('a', href=True)[0]
        prevDates = re.split('[（：）]', history.text)
        prevDate = d.datetime.strptime(f"{prevDates[0]} {prevDates[1].zfill(2)}:{prevDates[2].zfill(2)}",
                                       '%Y年%m月%d日 %H:%M')
        link = f"{rootZoo}{history['href']}"
    except Exception:
        link = prevDate = None
    return information, prevDate, link


def dataZooScrape(nativeTitle, airDate='', exclusions='', totalResults=1):
    episodeList = {}
    link, airDate = searchDataZoo(nativeTitle, airDate, exclusions, totalResults)
    while link:
        episodeList[airDate], airDate, link = dataZoo(link)
    return episodeList


## Searches kakaku.com for an entry in the timetable.
# nativeTitle (str) : EXACT Japanese title of the show
# startDate (datetime) : EXACT date the show airs on. May or may not be the first episode.
# Channel (str) : kakaku.com only stores information for NTV, TV Asahi, TBS, TV Tokyo, and Fuji TV
def getStartLink(nativeTitle, startDate, channel):
    channelNumber = networkDictionary[channel]
    attempt = 1
    date = d.datetime.strftime(startDate, '%Y%m%d')
    while True:
        try:
            soup = g.soup(f"{rootKakaku}/tv/channel={channelNumber}/date={date}")
            suffixLink = soup.find('a', string=nativeTitle).find_next('a')['href']
            print(f'Found the show on {date}')
            break
        except AttributeError:
            # The following will account for possible date mis-entries in MDL because of the 28HR system used in
            # Japanese TV
            print(f'Cannot find the show on {date}')
            date = d.datetime.strftime(startDate + d.timedelta(days=-(-1) ** attempt * (1 + (attempt > 2))), '%Y%m%d')
            attempt += 1
            if attempt > 4:
                print(
                    'Cannot find the show between dates {} - {}'.format(
                        d.datetime.strftime(startDate - d.timedelta(days=2), '%Y%m%d'),
                        d.datetime.strftime(startDate + d.timedelta(days=2), '%Y%m%d')
                    )
                )
                date = input('Provide a valid date in the exact format (YYYYMMDD) : ').replace(' ', '')
            if attempt == 6:
                exit('No valid dates. Either that or the title or the channel is incorrect/invalid')
    return suffixLink


def getEpisodes(nativeTitle, startDate, channel, omit=None, startEpisode=1):
    episodeSuffix = getStartLink(nativeTitle, startDate, channel)
    episodeList = {}
    seasonsList = {}
    episodeNumber = startEpisode
    episodeLinks = [episodeSuffix]
    while True:
        soup = g.soup(f"{rootKakaku}{episodeSuffix}")

        # Gets airdate information
        date = soup.find(attrs={'name': 'keywords'})['content'].split(',')[-2]
        time = soup.find(id='epiinfo').text.split('\u3000')[0].split(date)[1].split('〜')[0]
        start = d.datetime.strptime(g.japaneseDays(date, delimiter=['（', '）']) + time,
                                    '%Y年%m月%d日%a %H:%M')

        if int(d.datetime.strftime(start, '%y%m%d')) not in omit:
            episodeList[episodeNumber] = {'start': start,
                                          'cast': [],
                                          'guests': [],
                                          'url': f"{rootKakaku}{episodeSuffix}"}

            # Gets cast and guests information
            castInfo = [info for info in str(soup.find(id='epiinfo')).split('<br/>')[1:] if '\xa0' in info]
            if castInfo:
                for castDetails in castInfo:
                    castType, cast = castDetails.split('\xa0')
                    if castType in ['【出演】', '【声の出演】']:
                        episodeList[episodeNumber]['cast'] += [name.text.split('（')[0]
                                                               for name in bs(cast, 'lxml').find_all('a')]
                    else:
                        episodeList[episodeNumber]['guests'] += [name.text.split('（')[0]
                                                                 for name in bs(cast, 'lxml').find_all('a')]
            else:
                zooLink = searchDataZoo(nativeTitle, start)[0]
                episodeList[episodeNumber].update(dataZoo(zooLink)[0])

            if episodeList[episodeNumber]['start'].year not in list(seasonsList.keys()):
                seasonsList[episodeList[episodeNumber]['start'].year] = {
                    'start': episodeNumber,
                    'end': 0,
                    'startDate': episodeList[episodeNumber]['start']
                }
                try:
                    seasonsList[episodeList[episodeNumber]['start'].year - 1]['end'] = episodeNumber - 1
                except KeyError:
                    pass

            if episodeNumber % 1 == 0:
                print(f'Episode {episodeNumber} @ {start}')
        else:
            episodeNumber -= 1

        nextButton = soup.find(src='https://img1.kakaku.k-img.com/images/tv/2008/epi_next.gif')
        nextEpisode = nextButton.parent['href'] if nextButton else ''

        if nextEpisode:
            episodeNumber += 1
            episodeSuffix = nextEpisode
            episodeLinks.append(episodeSuffix)
        else:
            print(f"Scraped episodes {len(episodeList)}\nNo more epiosdes")
            break

    seasonsList[list(seasonsList)[-1]]['end'] = episodeNumber
    return episodeList, seasonsList


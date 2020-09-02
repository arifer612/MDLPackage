## Scrapes kakaku.com for episodes one at a time. (Do ping me if you find a better database on kakaku.com or elsewhere)
# This is accomplished in 3 parts:
#       1) Searches the timetable for the show. This is done in getStartLink()
#       2) Goes to the first episode's entry in kakaku.com and extracts the necessary information.
#       3) Finds the next episode in the episodes's page and repeats process. The last 2 steps are done in getEpisodes()

import datetime as d
from Library import general as g
from bs4 import BeautifulSoup as bs

root = 'https://kakaku.com'
rootZoo = 'https://datazoo.jp'
networkDictionary = {'NTV': 4, 'TV Asahi': 10, 'TBS': 6, 'TV Tokyo': 12, 'Fuji TV': 8}


## Searches kakaku.com for an entry in the timetable.
# nativeTitle (str) : EXACT Japanese title of the show
# startDate (dattime) : EXACT date the show airs on. May or may not be the first episode.
# Channel (str) : kakaku.com only stores information for NTV, TV Asahi, TBS, TV Tokyo, and Fuji TV
def getStartLink(nativeTitle, startDate, channel):
    channelNumber = networkDictionary[channel]
    attempt = 1
    date = d.datetime.strftime(startDate, '%Y%m%d')
    while True:
        try:
            soup = g.soup(f"{root}/tv/channel={channelNumber}/date={date}")
            suffixLink = soup.find('a', string=nativeTitle).find_next('a')['href']
            print(f'Found the show on {date}')
            break
        except AttributeError:
            # The following will account for possible date misentries in MDL because of the 28HR system used in
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


## Strips datetime format on kakaku.com
def airtime(datetime):
    time = datetime[-5:]
    dateFull = datetime.split('（')[0]
    date = dateFull[-len(dateFull.split('年')[-1]) - 5:]
    return d.datetime.strptime(date + time, '%Y年%m月%d日%H:%M')


def getEpisodes(nativeTitle, startDate, channel, omit=None, startEpisode=1):
    episodeSuffix = getStartLink(nativeTitle, startDate, channel)
    episodeList = {}
    seasonsList = {}
    episodeNumber = startEpisode
    episodeLinks = [episodeSuffix]
    while True:
        soup = g.soup(f"{root}{episodeSuffix}")

        # Gets airdate information
        date = soup.find(attrs={'name': 'keywords'})['content'].split(',')[-2]
        time = soup.find(id='epiinfo').text.split('\u3000')[0].split(date)[1].split('〜')[0]
        start = d.datetime.strptime(g.japaneseDays(date, delimiter=['（', '）']) + time,
                                    '%Y年%m月%d日%a %H:%M')

        if int(d.datetime.strftime(start, '%y%m%d')) not in omit:
            episodeList[episodeNumber] = {'start': start,
                                          'cast': [],
                                          'guests': [],
                                          'url': f"{root}{episodeSuffix}"}

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
                dataZoo(start, nativeTitle, episodeList[episodeNumber])

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


def dataZoo(airdate, nativeTitle, data):
    for i in range(1, 5):
        try:
            searchSoup = g.soup(f"{rootZoo}/d/{d.datetime.strftime(airdate, '%Y/%m/%d')}/{i}",
                                headers={'user-agent': 'Mozilla/5.0'})
            searchLink = f"{rootZoo}{searchSoup.find('a', text=nativeTitle)['href']}"
            episodeSoup = g.soup(searchLink)
            data['cast'] = [name.split('（')[0]
                 for name in episodeSoup.find('dd').text.replace('\n', '').split('\xa0')
                 if name and name != '-']
            data['url'] += f" and {rootZoo}/d/{d.datetime.strftime(airdate, '%Y/%m/%d')}/{i}"
            return data
        except AttributeError:
            pass
    raise FileNotFoundError

# TODO: Get details from https://datazoo.jp/tv/HKT48%E3%81%AE%E3%81%8A%E3%81%A7%E3%81%8B%E3%81%91%EF%BC%81/620522

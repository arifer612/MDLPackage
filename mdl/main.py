from mdl.Library import library
from mdl.Library import YouTubeAPI


class User:
    def __init__(self):
        self._cookies = library.login()

    def search(self, keyword, result=None):
        return library.search(keyword, result)

    def searchCast(self, name, nationality=None, gender=None):
        return library.castSearch(name, nationality, gender)

    def getShowDetails(self, link):
        return library.showDetails(link)

    def getAirDate(self, link, totalEpisodes=None, startEpisode=1):
        return library.getStartDate(link, totalEpisodes, startEpisode)

    def getRatings(self, link, start=1, end=False):
        return library.retrieveRatings(self._cookies, link, start, end)

    def getShowInfo(self, link):
        return library.showInfo(self._cookies, link)

    def getCastInfo(self, link):
        return library.castInfo(self._cookies, link)

    def submitCast(self, link, castList, notes=''):
        return library.castSubmit(self._cookies, link, castList, notes)

    def submitRatings(self, rating, details):
        return library.postRating(self._cookies, rating, details)

    def submitImage(self, link, file, fileDir, notes, epID=False, description='', **kwargs):
        return library.imageSubmit(self._cookies, link, file, fileDir, notes, epID, description, **kwargs)

    def submitSummary(self, epID, summary='', title='', notes=''):
        return library.summarySubmit(self._cookies, epID, summary, title, notes)

    def submitDelete(self, category=None, link=None, epID=None):
        return library.deleteSubmission(self._cookies, category, link, epID)

    def dramaList(self, **kwargs):
        return library.dramaList(self._cookies, **kwargs)


# Use this when making an updating bot
class Show:
    def __init__(self, keyword, result=None):
        self.__cookies = library.login()
        self.link = library.search(keyword, result)
        self.nativeTitle, self.network, self.totalEpisodes = library.showDetails(self.link)

    def getShowDetails(self):
        return library.showDetails(self.link)

    def getAirDate(self, totalEpisodes=None, startEpisode=1):
        return library.getStartDate(self.link, totalEpisodes, startEpisode)

    def getRatings(self, start=1, end=False):
        return library.retrieveRatings(self.__cookies, self.link, start,
                                       self.totalEpisodes if start == 1 and not end else end)

    def getShowInfo(self):
        return library.showInfo(self.__cookies, self.link)

    def getCastInfo(self):
        return library.castInfo(self.__cookies, self.link)

    def getSummaryInfo(self, episode):
        return library.retrieveSummary(self.__cookies, library.getEpisodeID(self.link, episode))

    def submitRatings(self, rating, details):
        return library.postRating(self.__cookies, rating, details)

    def submitCast(self, castList, notes=''):
        return library.castSubmit(self.__cookies, self.link, castList, notes)

    def submitImage(self, file, fileDir, notes, episode=None, description='', **kwargs):
        return library.imageSubmit(self.__cookies, self.link, file, fileDir, notes,
                                   library.getEpisodeID(self.link, episode) if episode else False, description, **kwargs)

    def submitSummary(self, episode=None, summary='', title='', notes=''):
        return library.summarySubmit(self.__cookies, library.getEpisodeID(self.link, episode) if episode else False,
                                     summary, title, notes)

    def submitDelete(self, category=None, episode=None):
        return library.deleteSubmission(self.__cookies, category, self.link,
                                        library.getEpisodeID(self.link, episode) if episode else False)


class YouTube:
    def __init__(self):
        self.__service = YouTubeAPI.login()

    def getThumbnails(self, videoID=None, playlistID=None, quality=0):
        return YouTubeAPI.getThumbnails(self.__service, videoId=videoID, playListId=playlistID, quality=quality)

from mdl.Library import library
import sys


def checkLink(function):
    def runFunction(self, *args, **kwargs):
        if not self.link:
            return print(f"Error: {repr(function.__name__)} requires a link. Use search() to set.")
        else:
            return function(self, *args, **kwargs)
    return runFunction


class User(object):
    def __init__(self, link=None, keyword=None, result=None):
        self.__cookies = library.login()
        self.link, self.keyword, self.result = link, keyword, result
        self.nativeTitle, self.network, self.totalEpisodes = None, None, None
        if self.link or self.keyword:
            self.search()

    def search(self, link=None, keyword=None, result=None):
        if self.link:
            self.link = self.link if not link else link
        elif self.keyword:
            self.link = library.search(self.keyword if not keyword else keyword, self.result if not result else result)
        elif not (keyword or link):
            print('Error: Provide either a search keyword or the link to the show')
        elif link:
            self.link = link
        else:
            self.link = library.search(keyword, result)
        if self.link:
            self.nativeTitle, self.network, self.totalEpisodes = library.showDetails(self.link)
        else:
            print('Search failed')

    @staticmethod
    def searchCast(name, nationality=None, gender=None):
        return library.castSearch(name, nationality, gender)

    @checkLink
    def getShowDetails(self):
        return library.showDetails(self.link)

    @checkLink
    def getAirDate(self, totalEpisodes=None, startEpisode=1):
        return library.getStartDate(self.link, totalEpisodes, startEpisode)

    @checkLink
    def getRatings(self, start=1, end=False):
        return library.retrieveRatings(self.__cookies, self.link, start,
                                       self.totalEpisodes if start == 1 and not end else end)

    @checkLink
    def getShowInfo(self):
        return library.showInfo(self.__cookies, self.link)

    @checkLink
    def getCastInfo(self):
        return library.castInfo(self.__cookies, self.link)

    @checkLink
    def getSummaryInfo(self, episode):
        return library.retrieveSummary(self.__cookies, library.getEpisodeID(self.link, episode))

    @checkLink
    def submitRatings(self, rating, details):
        return library.postRating(self.__cookies, rating, details)

    @checkLink
    def submitCast(self, castList, notes=''):
        return library.castSubmit(self.__cookies, self.link, castList, notes)

    @checkLink
    def submitImage(self, file, fileDir, notes, episode=None, description='', **kwargs):
        return library.imageSubmit(self.__cookies, self.link, file, fileDir, notes,
                                   library.getEpisodeID(self.link, episode) if episode else False, description, **kwargs)

    @checkLink
    def submitSummary(self, episode=None, summary='', title='', notes=''):
        return library.summarySubmit(self.__cookies, library.getEpisodeID(self.link, episode) if episode else False,
                                     summary, title, notes)

    @checkLink
    def submitDelete(self, category=None, episode=None):
        return library.deleteSubmission(self.__cookies, category, self.link,
                                        library.getEpisodeID(self.link, episode) if episode else False)

    def dramaList(self, **kwargs):
        if self.__class__ == Show:
            raise AttributeError("dramaList is not accessible through the 'Show' object")
        return library.dramaList(self.__cookies, **kwargs)


class Show(User):
    def __init__(self, link=None, keyword=None, result=None):
        if not (keyword or link):
            sys.exit('Error: Provide either a search keyword or the link to the show')
        super().__init__(link, keyword, result)

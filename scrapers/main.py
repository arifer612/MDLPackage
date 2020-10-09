from scrapers.Library import YouTubeAPI


class YouTubeObj:
    def __init__(self):
        self.__service = YouTubeAPI.login()

    def getThumbnails(self, videoID=None, playlistID=None, quality=0):
        return YouTubeAPI.getThumbnails(self.__service, videoId=videoID, playListId=playlistID, quality=quality)


YouTube = YouTubeObj()

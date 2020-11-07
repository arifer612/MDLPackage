from mdl.Library import library
import sys

from typing import Union, Tuple, Dict, Any
from datetime import datetime


def checkLink(function):
    def runFunction(self, *args, **kwargs):
        if not self.link:
            return print(f"Error: {repr(function.__name__)} requires a link. Use search() to set.")
        else:
            return function(self, *args, **kwargs)

    return runFunction


class User(object):
    """
    Signs into MDL as a user to view user statistics.
    """

    def __init__(self, keyword: str = None, result: int = None, link: str = None):
        """
        (Optional) Searches for a show on MDL to get statistics of.

        Args:
            keyword (str): Search keyword if `link` is not specified.
            result (int): Search result index. If not specified, the user will be prompted from a list.
            link (str): The MDL link to the show.
        """
        self.__cookies = library.login()
        self.__link, self.__keyword, self.__result = link, keyword, result
        self.__nativeTitle, self.__network, self.__totalEpisodes = None, None, None
        if self.__link or self.__keyword:
            self.search()

    @property
    def link(self) -> str:
        """Link to the MDL entry."""
        return self.__link

    @property
    def nativeTitle(self) -> str:
        """Native title of the show as reflected on MDL."""
        return self.__nativeTitle

    @property
    def network(self) -> str:
        """Network channel of the show as reflected on MDL."""
        return self.__network

    @property
    def totalEpisodes(self) -> int:
        """Total episodes of the show as reflected on MDL."""
        return self.__totalEpisodes

    def __repr__(self):
        return library.userProfile(self.__cookies)

    def search(self, keyword: str = None, result: str = None, link: str = None):
        """Searches MDL for the show and retrieves information of its native title, network, and total episodes.

        Args:
            keyword (str): Search keyword if `link` is not specified.
            result (int): Search result index. If not specified, the user will be prompted from a list.
            link (str): The MDL link to the show.
        """
        if self.__link or link:
            self.__link = self.__link if not link else link
        elif self.__keyword or keyword:
            self.__link = library.search(self.__keyword if not keyword else keyword,
                                         self.__result if not result else result)
        else:
            print('Error: Provide either a search keyword or the link to the show')
        if self.__link:
            self.__nativeTitle, self.__network, self.__totalEpisodes = library.showDetails(self.__link)
        else:
            print('Search failed')

    @staticmethod
    def searchCast(name: str, nationality: str = None, gender: str = None) -> int:
        """Searches for the cast ID of a cast on MDL.

        Args:
            name (str): Name of cast to search
            nationality (str): Filter search by nationality. If not specified, the filter will not be applied.
                               The available nationalities on MDL are `jp`, `ko`, `cn`, `hk`, `tw`, `th`, and `fp`.
            gender (str): Filter search by gender. If not specified, the filter will not be applied.
                          The available genders on MDL are `m`, and `f` only.

        Returns:
             Cast ID
        """
        return library.castSearch(name, nationality, gender)

    @checkLink
    def getShowDetails(self) -> Tuple[str, str, int]:
        """Extracts information of the show's original network and total posted episodes on MDL.

        Returns:
            Native title of the show on MDL.
            Network channel of the show on MDL.
            Total number of episodes posted on MDL.
        """
        return library.showDetails(self.link)

    @checkLink
    def getAirDate(self, episodeNumber: int = 1, totalEpisodes: int = None) -> datetime:
        """Gets episode air date. only works if there is at least 1 date posted on MDL.

        Args:
            episodeNumber (int): Episode to search air date for.
            totalEpisodes (int): Total number of episodes on MDL.

        Returns:
            Air date of the episode.
        """
        return library.getStartDate(self.link, totalEpisodes, episodeNumber)

    @checkLink
    def getRatings(self, start: int = 1, end: int = False):
        """Retrieves rating information of a show on MDL.

        Args:
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
        return library.retrieveRatings(self.__cookies, self.link, start,
                                       self.totalEpisodes if start == 1 and not end else end)

    @checkLink
    def getShowInfo(self) -> Tuple[dict, dict, Dict[Union[str, int], dict], Dict[str, Tuple[str, str, str, int]]]:
        """Parses all the information of the show episodes and season from MDL.

        Returns:
            info (dict): Latest JSON dictionary for the show information on MDL.
            releases (dict): Latest JSON dictionary for the show releases on MDL.
            episodes (dict): Full dictionary of all the episodes posted on MDL.
            seasons (dict): Full dictionary of all the seasons posted on MDL.
        """
        return library.showInfo(self.__cookies, self.link)

    @checkLink
    def getCastInfo(self) -> Tuple[dict, dict, str, str, dict]:
        """Parses all the information of the cast of the show from MDL

        Returns:
             castList (dict): Full dictionary of all the show cast on MDL.
             castRevision (dict): Latest JSON dictionary of updated show cast on MDL.
             weights (str): Weighted order of show cast on MDL.
             castURL (str): Redirect link to update the show cast on MDL.
             params (dict): Request parameters to update the show cast on MDL.
        """
        return library.castInfo(self.__cookies, self.link)

    @checkLink
    def getSummaryInfo(self, episode: int) -> Dict[str, str]:
        """Retrieves the episode summary from MDL.

        Args:
            episode (int): Episode number.

        Returns:
            A dictionary with the episode title and summary.
        """
        return library.retrieveSummary(self.__cookies, library.getEpisodeID(self.link, episode))

    @checkLink
    def submitRatings(self, rating: Dict[str, Union[Tuple[int, int], Dict[str, Union[int, float]], str]],
                      details: Dict[str, Union[int, float, str]] = None) -> bool:
        """Post personal ratings to MDL.

        Args:
            rating (dict): Basic rating information required to post to MDL. Same structure as the return of
                           retrieveRating()
            details (dict): [DEPRECATED] More detailed information to include into the rating. The possible keys are:
                            `dropped`, `spoiler`, `completed`, `episode_seen`, `review_headline`, `story_rating`,
                            `acting_rating`, `music_rating`, `rewatch_rating`, `overall_rating`

        Returns:
            Boolean result of the successful post/patch.
        """
        return library.postRating(self.__cookies, rating, details)

    @checkLink
    def submitCast(self, castList: dict, notes: str = '') -> None:
        """Posts the updated cast list to MDL

        Args:
            castList (dict): Dictionary of cast members and a list of episodes they starred in.
                             e.g. {'cast1': [1, 2, 4, 5, 6], 'cast2': ...}
            notes (str): Notes for the reviewing staff to read.
        """
        return library.castSubmit(self.__cookies, self.link, castList, notes)

    @checkLink
    def submitImage(self, file: str, fileDir: str, notes: str, episode: int = None, description: str = '', **kwargs)\
            -> bool:
        """Posts an image to MDL.

        Args:
            file (str): Filename with its extension.
            fileDir (str): Directory to where the file is stored in.
            notes (str): Title of the image if uploading a photo or notes for the approving staff to read if uploading
                            an episode cover.
            episode (int): Episode number if uploading an episode cover. If not specified, the image will upload as a
                           normal photo by default.
            description (str): Description of a photo. Only if the image is uploaded as normal photo.

        Returns:
            True if the image has been posted and False otherwise.
        """
        return library.imageSubmit(self.__cookies, self.link, file, fileDir, notes,
                                   library.getEpisodeID(self.link, episode) if episode else False, description,
                                   **kwargs)

    @checkLink
    def submitSummary(self, episode: int = None, summary: str = '', title: str = '', notes: str = '') -> bool:
        """Updates the episode summary on MDL.

        Args:
            episode (int): Episode number.
            summary (str): Episode summary text.
            title (str): Episode title test.
            notes (str): Notes for the reviewing staff to read.

        Returns:
            True if the information was successfully posted to MDL and False otherwise.
        """
        return library.summarySubmit(self.__cookies, library.getEpisodeID(self.link, episode) if episode else False,
                                     summary, title, notes)

    @checkLink
    def submitDelete(self, category: str = None, episode: int = None):
        """Deletes a submission on MDL.

        Args:
            category (str): Category of submission to delete.
                            e.g. cast, image etc.
            episode (int): Episode number.

        Returns:
            True if deletion is successful and False otherwise.
        """
        return library.deleteSubmission(self.__cookies, category, self.link,
                                        library.getEpisodeID(self.link, episode) if episode else False)

    def dramaList(self, *category) -> Dict[str, Dict[int, Dict[str, Any]]]:
        """Parses user's drama list and returns it as a navigable dictionary.

        Args:
            category: The available categories are `watching`, `completed,` plan_to_watch`, `hold`, `drop`,
                      `not_interested`

        Returns:
            The user's drama list as a dictionary.
        """
        if self.__class__ == Show:
            raise AttributeError("dramaList is not accessible through the 'Show' object")
        return library.dramaList(self.__cookies, *category)


class Show(User):
    """Manage a specific show on MDL. A subclass of the User() superclass."""
    def __init__(self, keyword=None, result=None, link=None):
        if not (keyword or link):
            sys.exit('Error: Provide either a search keyword or the link to the show')
        super().__init__(keyword, result, link)

    def __repr__(self):
        return f"{super().__repr__()} @ {self.nativeTitle}"

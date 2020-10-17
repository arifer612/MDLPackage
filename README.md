# MDLPackage
A package of libraries used for scraping information on Japanese TV shows from official sites to post on MyDramaList.com

# Table of Contents
- [Setup](#setup)
    - [Requirements](#requirements)
    - [Installation](#isntallation)
- [Documentation](#documentation)
    - [mdl](#mdl)
    - [general]
    - [scrapers]

# Setup
## Requirements

    python >= 3.6

This package has only been tested in a Linux and Windows 10 environment using Python 3.6.9. Translatability to MacOS or other versions of Python cannot be assured, but earlier versions of Python will probably not be able to support several features. 

## Installation
1. Clone the package from GitHub and run setup.py to install.

        git clone https://github.com/arifer612/MDLPackage
        cd MDLPackage
        python setup.py

2. Install using pip, while remembering to install the necessary dependencies when needed.

        pip install -i https://test.pypi.org/simple/ MDLPackage
        
# Documentation
## mdl
There are 2 objects that can be called from this package: **mdl.User()** and **mdl.Show()**

####**mdl.User()** 
Logs in as a user to retrieve or post information on MyDramaList.com without the need for an API key, using only the user's MyDramaList username and password. This class requires no arguments. *(This will be expanded in [Login Details])* The actions that can be used on **User()** are as follows.

    m = mdl.User()
    
    m.search(keyword, result=None)
Searches for show using *keyword (str)*. Returns a list of matching results unless there is only 1 result or the result number is pre-emptively declared as *result (int)*

    m.searchCast(name, nationality=None, gender=None)
Searches for the display name of a cast used in MyDramaList. *name (str)* may either be in English or the cast's native name. *nationality (str)* filters the results by nationality. Options availabe are *(Japanese, Jp), (Korean, Ko), (Chinese, Cn), (Hong Kongers, Hk), (Taiwanese, Tw), (Thai, Th), (Filipino, Fp)*. *gender (str)* filters the results by gender. Options available are *(Male, M), (Female, F)*.

    m.getShowDetails(link)
Retrieves the native title, network name, and total number of posted episodes from the show's link passed in *link (str)*.

    m.getAirDate(link, totalEpisodes=None, startEpisode=1)
Gets information of the first episode of the show given by its link in *link (str)*, or the episode passed in *startEpisode (int)*. 

    m.getRatings(link, start=1, end=False)
Returns a list of the user's and MDL average rating of every episode of the show given by its link in *link (str)*. For a fixed number of episodes, passing episode numbers in *start (int)* and *end (int)* will limit the results. The ratings for each episode will be passed as a dictionary.

    m.getShowInfo(link)
Gets posted information of the show given by its link in *link (str)* for editing. 

    m.getCastInfo(link)
Gets posted information of the show's cast given by its link in *link (str)* for editing. 

    m.getSummaryInfo(link, episode)
Gets psoted information of the show's title and summary given by its link in *link (str)* and episode number in *episode (int)*, for editing.

    m.submitCast(link, castList, notes='')
Posts a new updated cast list of a show given by its link in *link (str)* onto MDL. The updated cast list in *castList (dict)* will be compared against the currently posted cast list in MDL. Only differences in the two lists will be posted. *notes (str)* will be read by MDL administrators and staff when reviewing updates.

    m.submitRatings(rating, details=None)
Posts or updates user's ratings of a show epiosde. *rating (dict)* is retrieved from **m.getRatings()**.

    m.submitImage(link, file, fileDir, notes, episode=None, description='')
Posts an image on MDL. If an episode number is passed in *episode (int)*, the image will be posted as an episode cover, otherwise it will be posted as a photo in the show's album. The file name is given in *file (str)* and the directory folder it is stored in *fileDir (str)*. For episode covers, *notes (str)* will be read by MDL administrators and staff when reviewing the update; for photos, it will be the title of the posted image and the description of the photo is given in *description (str)*.

    m.submitSummary(link, episode, summary='', title='', notes='')
Updates the title (from *title (str)*) or summary (from *summary (str)*) of an episode given by *episode (int)* for a show given by its link in *link (str)*. *notes (str)* will be read by MDL administrators and staff when reviewing the update.

    m.submitDelete(category, link, episode=None)
Deletes/reset any user made update or submission to a show given by its link in *link (str)* or an episode given by its episode number in *episode (int)*. The submission categories that can be deleted/reseted are *'details', 'cover', 'cast'*

    m.dramaList()
Retrieves the user's drama list with information such as date started watching, date ended watching etc. More details can be found in [exportMDL](https://github.com/arifer612/exportMDL).


####**mdl.Show()** 
Logs in as a user to retrieve or post information for a specific show on MyDramaList.com using only the user's MyDramaList username and password. When writing scripts or bots to post on the site, using this class over **User()** is preferable. This class requires at least 1 argument.

    mdl.Show(showTitle='', result=None, link='')
    
Either *showTitle* or *link* is required. Provide the link to the show as *link*. Otherwise, using *showTitle* will search MyDramaList.com for the show and return a list of matching shows unless there is only 1 show or the result number is declared in *result*. *link* takes priority over *showTitle*.

## general
There are 2 objects in this module: **general.configFile** and **general.LogFile**. The other methods in this package serve as a library of general methods.

####**general.configFile**
A global configuration file may be created in ~/.config/MDLConfig.conf. Stores information of where the login key file and log directory are. Without the global configuration file, the default directories are:
    
    key file: ~/.MDL.conf
    log directory: ~/Documents/Logs
    
Changing the directories are done through **general.configFile.move()**
    
    general.configFile.move(key='', log='')
    
It is also possible to set the login keys without accessing the key file directly through **general.configFile.newKeys()**

    general.configFile.newKeys(username='MDL Username', password='MDL Password', youtubeAPI='YouTube API key', echo=True)

####**general.LogFile**
A log file object to manage the various logs of each episode and show for MyDramaList. The data structure is similar to that of a dictionary but with several new methods meant to add data efficiently. The log file will be physically saved on disk as a pickle but it is possible to convert it to the human readable YAML format for editing. The methods which may be used on **general.LogFile** are as follows:

    log = general.LogFile(fileName, rootDir='.', flip=False)
    
    log.add(key, data=None, force=False)
Adds data to the log file. **key** may be a dictionary of data. If **key** is not a dictionary, **data** will be added to the 

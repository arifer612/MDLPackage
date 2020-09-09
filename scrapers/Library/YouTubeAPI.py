from googleapiclient.discovery import build
import googleapiclient.errors
from scrapers import configFile
from configparser import ConfigParser
from distutils.util import strtobool


def login():
    keys = ConfigParser()
    keys.read(configFile._Config__keyDir)
    key = keys['USER']['youtubeAPI'] if keys['USER']['youtubeAPI'] else input('API key: ')
    response = build('youtube', 'v3', developerKey=key)
    if response and key != keys['USER']['youtubeAPI']:
        answer = strtobool(input('Save API in key configuration?'))
        if answer:
            keys['USER']['youtubeAPI'] = key
            with open(configFile._Config__keyDir, 'w') as r:
                keys.write(r)
            print('Saved key')
        else:
            print('Key not saved')
    return response


def getPlayList(youtube, playlistId, pageToken=None, maxResults=50, **kwargs):
    playlist = []
    while True:
        page = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlistId,
            pageToken=pageToken,
            maxResults=maxResults,
            **kwargs
        ).execute()
        playlist += page['items']
        if 'nextPageToken' in page:
            pageToken = page['nextPageToken']
        else:
            break
    return playlist


def getVideoInfo(youtube, videoId):
    return youtube.videos().list(
        part='snippet',
        id=videoId
    ).execute()


def getThumbnails(youtube, videoId=None, playListId=None, quality=0):
    qualityDict = {
        0: 'maxres',
        1: 'high',
        2: 'medium',
        3: 'standard',
        4: 'default'
    }
    if videoId:
        playlist = getVideoInfo(youtube, videoId=videoId)
    elif playListId:
        playlist = getPlayList(youtube, playListId)
    else:
        return None

    def getThumbnail(video, q):
        while q in qualityDict:
            try:
                return video['snippet']['thumbnails'][qualityDict[q]]['url']
            except KeyError:
                q += 1
        return None

    return [{
        'title': i['snippet']['title'],
        'thumbnail': getThumbnail(i, quality),
        'url': f"https://www.youtube.com/watch?v={i['snippet']['resourceId']['videoId']}"
    } for i in playlist
        if i['snippet']['title'] != 'Private video']

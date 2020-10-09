import general as g

root = 'https://www.tv-osaka.co.jp'


def getImages(title, forced=False):
    episode, archives = 0, {}
    for episode, link in enumerate(g.soup(f"{root}/{title}/js/get_story.js").find_all('a'), start=1):
        archives[episode] = f"{root}{link['href']}"
    if forced:
        archives[episode + 1] = archives[episode].replace(str(episode).zfill(2), str(episode + 1).zfill(2))
    return {epNum: [{
        'url': link,
        'keyNotes': f"TV Osaka Gallery Episode {epNum} ",
        'description': "Official scene shots" if block.h1.text == '場面写真' else "Official offshoots",
        'images': [image['src'] for image in block.find_all('img')]
    } for block in g.soup(link).find_all(class_='photos')
    ] for epNum, link in archives.items()
    } if archives else None

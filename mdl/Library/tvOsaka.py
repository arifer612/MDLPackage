from mdl.Library import general

root = 'https://www.tv-osaka.co.jp'


def getImages(title):
    archives = {
        int(link['href'].split('/')[-2]): f"{root}{link['href']}"
        for link in general.soup(f"{root}/{title}/js/get_story.js").find_all('a')
    }
    return {epNum: [{
        'url': link,
        'keyNotes': f"TV Osaka Gallery Episode {epNum} ",
        'description': "Official scene shots" if block.h1.text == '場面写真' else "Official offshoots",
        'images': [image['src'] for image in block.find_all('img')]
    } for block in general.soup(link).find_all(class_='photos')
    ] for epNum, link in archives.items()
    } if archives else None

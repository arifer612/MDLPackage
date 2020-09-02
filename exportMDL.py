from Library import *
import sys
import getopt


def exportList(fileName, watching, complete, hold, drop, plan_to_watch, not_interested):
    keys = library.login()
    dramaList = library.dramaList(keys, watching, complete, hold, drop, plan_to_watch, not_interested)
    with open(os.path.join(logDir, f"{fileName}.tsv"), 'w') as f:
        f.write(f"Show ID\tTitle\tStatus\tEpisodes Watched\tTotal Episodes\tCountry of Origin\t"
                f"Show Type\tRating\tDate Started\tDate Ended\tRe-watched\n")
        f.writelines([
            f"{showID}\t{show['title']}\t{status}\t{show['progress']}\t{show['total']}\t{show['country']}\t"
            f"{show['type']}\t{show['rating']}\t{str(show['date-start']).split(' ')[0] if show['date-start'] else ''}\t"
            f"{str(show['date-end']).split(' ')[0] if show['date-end'] else ''}\t{show['rewatched']}\n"
            for status in dramaList if dramaList[status] for showID, show in dramaList[status].items()
        ])
    print(f"File saved as {os.path.join(logDir, f'{fileName}.tsv')}")


def main(argv):
    fileName = 'MyDramaList'
    watching = complete = hold = drop = plan_to_watch = not_interested = True
    try:
        opts, args = getopt.getopt(argv, "f:he:", ['filename=', 'help', 'except='])
        for opt, arg in opts:
            if opt in ['-f', '--filename']:
                fileName = arg
            if opt in ['-e', '--except']:
                exceptions = arg.split(',')
                watching -= 'watching' in exceptions
                complete -= 'complete' in exceptions
                hold -= 'hold' in exceptions
                drop -= 'drop' in exceptions
                plan_to_watch -= 'plan_to_watch' in exceptions
                not_interested -= 'not_interested' in exceptions

            if opt in ['-h', '--help']:
                print('-----------------------------------------------------------------------------------------\n'
                      '------------This script exports your dramalist from MyDramaList.com----------------------\n'
                      '\n'
                      'Use the configuration file to set the directory to save your login details.\n'
                      '\n'
                      'usage: exportFile.py [-f --filename <filename>] [--help]\n'
                      '                     [-e --exception <exception1,exception2...>]\n'
                      '\n'
                      '-f     Specifies filename\n\n'
                      '-e     Specifies list exceptions. Exceptions MUST be separated by a comma without spaces.\n'
                      '       The available options are:\n'
                      '       (watching, complete, hold, drop, plan_to_watch, not_interested)\n'
                      '\n'
                      '-------------------Leave the filename unset to use default filename----------------------\n'
                      '-----------------------------------------------------------------------------------------'
                      )
                sys.exit()
    except getopt.GetoptError:
        pass
    exportList(fileName)


if __name__ == '__main__':
    main(sys.argv[1:])

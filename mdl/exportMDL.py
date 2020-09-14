from .main import User
import os
import sys
import getopt
from mdl import configFile


def main(argv):
    logDir = configFile.logDir
    fileName = 'MyDramaList'
    watching = completed = hold = drop = plan_to_watch = not_interested = True

    def usage():
        print('-----------------------------------------------------------------------------------------\n'
              '--------This script exports your drama list as a .tsv file from MyDramaList.com----------\n'
              '\n'
              'Use the configuration file to set the directory to save your login details.\n'
              '\n'
              'usage: exportMDL.py [-f --filename <filename>] [--help]\n'
              '                    [-e --exception <exception1,exception2...>]\n'
              '\n'
              '-f     Specifies filename\n\n'
              '-e     Specifies list exceptions. Exceptions MUST be separated by a comma without spaces.\n'
              '       The available options are:\n'
              '       (watching, completed, hold, drop, plan_to_watch, not_interested)\n'
              '\n'
              '-h     Shows the help page'
              '\n'
              '-------------------Leave the filename unset to use default filename----------------------\n'
              '-----------------------------------------------------------------------------------------'
              )

    try:
        opts, args = getopt.getopt(argv, "f:he:o:", ['filename=', 'help', 'except=', 'only='])
        for opt, arg in opts:
            if opt in ['-f', '--filename']:
                fileName = arg
            if opt in ['-e', '--except']:
                exceptions = arg.split(',')
                watching -= 'watching' in exceptions
                completed -= 'completed' in exceptions
                hold -= 'hold' in exceptions
                drop -= 'drop' in exceptions
                plan_to_watch -= 'plan_to_watch' in exceptions
                not_interested -= 'not_interested' in exceptions
            if opt in ['-o', '--only']:
                overwrite = arg.split(',')
                watching = 'watching' in overwrite
                completed = 'completed' in overwrite
                hold = 'hold' in overwrite
                drop = 'drop' in overwrite
                plan_to_watch = 'plan_to_watch' in overwrite
                not_interested = 'not_interested' in overwrite
            if opt in ['-h', '--help']:
                usage()
                sys.exit()
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    user = User()
    myDramaList = user.dramaList(watching=watching, completed=completed, hold=hold, drop=drop,
                                 plan_to_watch=plan_to_watch, not_interested=not_interested)

    with open(os.path.join(logDir, f"{fileName}.tsv"), 'w', encoding='utf-8-sig') as e:
        e.write(f"Title\tStatus\tEpisodes watched\tTotal episodes\t"
                f"Country of Origin\tShow type\tRating\t"
                f"Started on\t"
                f"Ended on\tRe-watched\n")
        e.writelines([
            f"{show['title']}\t{status.replace('_', ' ').capitalize()}\t{show['progress']}\t{show['total']}\t"
            f"{show['country']}\t{show['type']}\t{show['rating']}\t"
            f"{str(show['date-start']).split(' ')[0] if show['date-start'] else ''}\t"
            f"{str(show['date-end']).split(' ')[0] if show['date-end'] else ''}\t{show['rewatched']}\n"
            for status in myDramaList if myDramaList[status] for show in myDramaList[status].values()
        ])
    print(f"File saved as {os.path.join(logDir, f'{fileName}.tsv')}")


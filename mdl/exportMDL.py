from .main import User
import os
from mdl import configFile
from optparse import OptionGroup, OptionParser


def main(argv):
    logDir = configFile.logDir
    parser = OptionParser()
    parser.set_defaults(only=False, quiet=False)
    parser.add_option('-f', '--filename', action='store', dest='filename', help='Specifies FILENAME of export list')
    parser.add_option('-o', '--only', action='store_true', dest='only', help='Filters list categories')
    parser.add_option('-e', '--exception', action='store_false', dest='only', help='Specifies list exceptions')
    parser.add_option('-q', '--quiet', action='store_true', dest='quiet', help='Hides progress bar')

    group = OptionGroup(parser, 'Categories to filter list')
    group.add_option('-w', '--watching', action='store_true', dest='w', default=False)
    group.add_option('-c', '--completed', action='store_true', dest='c', default=False)
    group.add_option('-k', '--hold', action='store_true', dest='k', default=False)
    group.add_option('-d', '--drop', action='store_true', dest='d', default=False)
    group.add_option('-p', '--plan_to_watch', '--ptw', action='store_true', dest='p', default=False)
    group.add_option('-n', '--not_interested', '--ni', action='store_true', dest='n', default=False)
    parser.add_option_group(group)

    opt, arg = parser.parse_args(argv)
    if any([opt.w, opt.c, opt.k, opt.d, opt.p, opt.n]):
        [opt.w, opt.c, opt.k, opt.d, opt.p, opt.n] = [i * opt.only for i in [opt.w, opt.c, opt.k, opt.d, opt.p, opt.n]]
    else:
        [opt.w, opt.c, opt.k, opt.d, opt.p, opt.n] = [not i for i in [opt.w, opt.c, opt.k, opt.d, opt.p, opt.n]]
    user = User()
    myDramaList = user.dramaList(watching=opt.w, completed=opt.c, hold=opt.k, drop=opt.d,
                                 plan_to_watch=opt.p, not_interested=opt.n, suppress=opt.quiet)
    fileName = 'MyDramaList' if not opt.filename else opt.filename

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

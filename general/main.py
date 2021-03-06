import os
import sys
from . import readableLog, machinableLog, LogFile
from . import configFile
from optparse import OptionParser, OptionGroup


def main(argv):
    parser = OptionParser(prog='general', version=f"MDLPackage v{configFile.version}")
    parser.set_defaults(showDir=False, quiet=False)
    parser.add_option('-d', '--directory', action='store_true', dest='showDir', default=False,
                      help='Shows log directory and key filepath.')
    parser.add_option('-q', '--quiet', action='store_true', dest='quiet', default=False,
                      help='Suppresses output to the minimum')

    logGroup = OptionGroup(parser, "Log file conversion")
    logGroup.add_option('-r', '--read', type='string', action='store', dest='readLogs',
                        help='Makes log file readable')
    logGroup.add_option('-w', '--write', type='string', action='store', dest='writeLogs',
                        help='Converts readable log file back into machine file')
    parser.add_option_group(logGroup)

    dirGroup = OptionGroup(parser, "Change directories",
                           "Change the directories important for the package to work")
    dirGroup.add_option('-l', '--log', type='string', action='store', dest='logDir', metavar='DIR',
                        help='Moves log directory to DIR')
    dirGroup.add_option('-k', '--key', type='string', action='store', dest='keyDir', metavar='DIR',
                        help='Moves login key filepath to DIR')
    parser.add_option_group(dirGroup)

    opt, arg = parser.parse_args(argv)
    if opt.showDir:
        print(f"Log directory:\t\t {configFile.logDir}\n"
              f"Key filepath:\t\t {configFile._Config__keyDir}")
        sys.exit(0)
    if opt.readLogs:
        fileDir, file = os.path.split(opt.readLogs)
        readableLog(file, fileDir)
        sys.exit(f"A readable logs has been created in {readableLog(file, fileDir)}") if not opt.quiet else sys.exit(0)
    elif opt.writeLogs:
        fileDir, file = os.path.split(opt.writeLogs)
        machinableLog(file, fileDir)
        sys.exit(f"The readable log has been dumped as a pickle") if not opt.quiet else sys.exit(0)

    configFile.move(log=opt.logDir, key=opt.keyDir)

import os
import sys
import getopt
from .Library.library import readableLog, machinableLog


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'r:w:', ['read=', 'write='])
        for opt, arg in opts:
            fileDir, file = os.path.split(arg)
            if opt in ['-r', '--read']:
                sys.exit(f"A readable logs has been created in {readableLog(file, fileDir)}")
            if opt in ['-w', '--write']:
                machinableLog(file, fileDir)
                sys.exit(f"The readable log has been dumped as a pickle")
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

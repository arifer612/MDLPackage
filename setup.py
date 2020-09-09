import setuptools
import sys
from distutils.util import strtobool
from mdl import configFile  # To create default configuration files and folders

if sys.version_info <= (3, 6):
    print('mdl has only been tested on Python >= 3.6. Continue installing?')
    try:
        answer = strtobool(input('(y/n)'))
        if answer:
            pass
        else:
            raise ValueError
    except ValueError:
        sys.exit(1)

with open("requirements.txt", "r") as fr:
    install_requires = fr.read()

with open("README.md", "r") as fR:
    long_description = fR.read()

version = '0.0.8'

setuptools.setup(
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    name="mdl",
    version=version,
    author="arifer612",
    description="Bots for scraping and posting information onto MyDramaList.com",
    include_package_data=True,
    install_requires=install_requires,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/arifer612/mdl",
    packages=setuptools.find_packages(),
    package_data={
        'mdl': ['MDLConfig.conf'],
    },
    python_requires=">=3.6",
)

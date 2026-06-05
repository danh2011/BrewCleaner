# BrewCleaner
![MacOS badge](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=apple&logoColor=white) ![python language badge](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
BrewCleaner is open-source software for macOS which helps users to find issues with Homebrew & fix them.

## Requirements
BrewCleaner needs the following installed:
 - Python 3.8+ (pre-installed with macOS)
 - macOS 10.5+
 
BrewCleaner will install the following Python requirements to run correctly:
 - tkinter
 - customtkinter

If you already have any of the Python packages, BrewCleaner will detect this.
If you need a newer version of Python, please install it via [this link](https://www.python.org/downloads/).

## Install & Running
In the Terminal, run the following command to download the script and move it to `Applications`:

    wget https://raw.githubusercontent.com/danh2011/BrewCleaner/refs/heads/main/brewcleaner.py && mv brewcleaner.py /Applications/

Then `cd` (change directory) into `Applications` and run  the file via:

    python3 brewcleaner.py

This will cause Python Launcher to open and BrewCleaner will open onto the TOS page.
**You have now installed BrewCleaner!**

## Contributing
We would love if you want to contribute. This began as a solo project when I kept breaking my Homebrew with a slow internet connection and being left with locked par-installed bottles & formulas. I want to make this the best it can be as I (and many others, I'm sure) will genuinely need this. Thank you.

### License
BrewCleaner is protected by the GNU General Public License v3. You can view it [here].(https://github.com/danh2011/BrewCleaner/blob/main/LICENSE)

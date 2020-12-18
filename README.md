
# MyCowboy - OS X Menubar plugin

Displays information regarding your Cowboy bike in the Mac OS X menubar. Allows you to remotely control your Cowboy bike as well.

![Imgur](https://i.imgur.com/Q45iFOP.png)


## Changelog: 

**Update 2019.08.11:**
- [X] Show bike model, serial, mac address, odometer, co2 saved
- [X] Enable continuous bike tracking
- [X] Fix OS X dark mode icon

**Update 2019.07.26:**
- [X] alpha version 
- [X] Initial import

## Credits: 

Samuel Dumont's python Cowboy [class](https://gitlab.com/samueldumont/python-cowboy-bike).

## Licence: GPL v3

## Installation instructions: 

1. Ensure you have [bitbar](https://github.com/matryer/bitbar/releases/latest) installed.
2. Execute 'sudo easy_install requests tinydb==3.9 keyring==8.7 pathos pyobjc-framework-CoreLocation googlemaps' in Terminal.app
3. Ensure your bitbar plugins directory does not have a space in the path (A known bitbar bug)
4. Copy [mycowboy.15m.py](mycowboy.15m.py) and library directory with its files to your bitbar plugins folder and chmod +x the file from your terminal in that folder
5. Run bitbar

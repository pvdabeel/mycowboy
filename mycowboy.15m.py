#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# <bitbar.title>MyCowboy</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>pvdabeel@mac.com</bitbar.author>
# <bitbar.author.github>pvdabeel</bitbar.author.github>
# <bitbar.desc>Control your Cowboy Bike from the Mac OS X menubar</bitbar.desc>
# <bitbar.dependencies>python</bitbar.dependencies>
#
# Licence: GPL v3

# Installation instructions: 
# -------------------------- 
# Execute in terminal.app before running : 
#    sudo easy_install keyring
#    sudo easy_install pyicloud
#    sudo easy_install pyobjc-framework-CoreLocation
#
# Ensure you have bitbar installed https://github.com/matryer/bitbar/releases/latest
# Ensure your bitbar plugins directory does not have a space in the path (known bitbar bug)
# Copy this file to your bitbar plugins folder and chmod +x the file from your terminal in that folder
# Run bitbar

_DEBUG_ = False 

# Disabled if you don't want your bike location to be tracked to a DB

_LOCATION_TRACKING_ = True

try:   # Python 3 dependencies
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen, build_opener
    from urllib.request import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler, HTTPError, URLError
except: # Python 2 dependencies
    from urllib import urlencode
    from urllib2 import Request, urlopen, build_opener
    from urllib2 import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler, HTTPError, URLError


import ast
import json
import sys
import datetime
import calendar
import base64
import math
import keyring                                  # Cowboy access token is stored in OS X keychain
import getpass                                  # Getting password without showing chars in terminal.app
import time
import os
import subprocess
import pyicloud                                 # Icloud integration - retrieving calendar info 
import requests
import binascii

import CoreLocation as cl

from pyicloud   import PyiCloudService          # Icloud integration - schedule events in icloud agenda
from datetime   import date
from tinydb     import TinyDB                   # Keep track of location and cowboy states
from os.path    import expanduser
from googlemaps import Client as googleclient   # Reverse lookup of addresses based on coordinates


# Location where to store state files
home         = expanduser("~")
state_dir    = home+'/.state/mycowboy'

if not os.path.exists(state_dir):
    os.makedirs(state_dir)


# Location tracking database
locationdb = TinyDB(state_dir+'/mycowboy-locations.json')


# Nice ANSI colors
CEND    = '\33[0m'
CRED    = '\33[31m'
CGREEN  = '\33[32m'
CYELLOW = '\33[33m'
CBLUE   = '\33[34m'

# Support for OS X Dark Mode
DARK_MODE=os.getenv('BitBarDarkMode',0)


# Convertor for distance
def convert_distance(distance_unit,distance):
    if distance_unit == 'km':
        return math.ceil(distance * 160.9344)/100
    else:
        return distance

        
# Pretty print bike lock state 
def lock_state(locked):
    if bool(locked):
        return CGREEN + 'Locked' + CEND
    else:
        return CRED + 'Unlocked' + CEND


# Function to retrieve goole map & sat images for a given location
def retrieve_google_maps(latitude,longitude):
   todayDate = datetime.date.today()
    
   try:
      with open(state_dir+'/mytesla-location-map-'+todayDate.strftime("%Y%m")+'-'+latitude+'-'+longitude+'.png') as location_map:
         my_img1 = base64.b64encode(location_map.read())
         location_map.close()
      with open(state_dir+'/mytesla-location-sat-'+todayDate.strftime("%Y%m")+'-'+latitude+'-'+longitude+'.png') as location_sat:
         my_img2 = base64.b64encode(location_sat.read())
         location_sat.close()
   except: 
      with open(state_dir+'/mytesla-location-map-'+todayDate.strftime("%Y%m")+'-'+latitude+'-'+longitude+'.png','w') as location_map, open(state_dir+'/mytesla-location-sat-'+todayDate.strftime("%Y%m")+'-'+latitude+'-'+longitude+'.png','w') as location_sat:
         my_google_key = '&key=AIzaSyBrgHowqRH-ewRCNrhAgmK7EtFsuZCdXwk'
         my_google_dark_style = ''
                
         if bool(DARK_MODE):
            my_google_dark_style = '&style=feature:all|element:labels|visibility:on&style=feature:all|element:labels.text.fill|saturation:36|color:0x000000|lightness:40&style=feature:all|element:labels.text.stroke|visibility:on|color:0x000000|lightness:16&style=feature:all|element:labels.icon|visibility:off&style=feature:administrative|element:geometry.fill|color:0x000000|lightness:20&style=feature:administrative|element:geometry.stroke|color:0x000000|lightness:17|weight:1.2&style=feature:administrative.country|element:labels.text.fill|color:0x838383&style=feature:administrative.locality|element:labels.text.fill|color:0xc4c4c4&style=feature:administrative.neighborhood|element:labels.text.fill|color:0xaaaaaa&style=feature:landscape|element:geometry|color:0x000000|lightness:20&style=feature:poi|element:geometry|color:0x000000|lightness:21|visibility:on&style=feature:poi.business|element:geometry|visibility:on&style=feature:road.highway|element:geometry.fill|color:0x6e6e6e|lightness:0&style=feature:road.highway|element:geometry.stroke|visibility:off&style=feature:road.highway|element:labels.text.fill|color:0xffffff&style=feature:road.arterial|element:geometry|color:0x000000|lightness:18&style=feature:road.arterial|element:geometry.fill|color:0x575757&style=feature:road.arterial|element:labels.text.fill|color:0xffffff&style=feature:road.arterial|element:labels.text.stroke|color:0x2c2c2c&style=feature:road.local|element:geometry|color:0x000000|lightness:16&style=feature:road.local|element:labels.text.fill|color:0x999999&style=feature:transit|element:geometry|color:0x000000|lightness:19&style=feature:water|element:geometry|color:0x000000|lightness:17'
       
         my_google_size = '&size=360x315'
         my_google_zoom = '&zoom=17'
         my_url1 ='https://maps.googleapis.com/maps/api/staticmap?center='+latitude+','+longitude+my_google_key+my_google_dark_style+my_google_zoom+my_google_size+'&markers=color:red%7C'+latitude+','+longitude
         my_url2 ='https://maps.googleapis.com/maps/api/staticmap?center='+latitude+','+longitude+my_google_key+my_google_zoom+my_google_size+'&maptype=hybrid&markers=color:red%7C'+latitude+','+longitude
         my_cnt1 = requests.get(my_url1).content
         my_cnt2 = requests.get(my_url2).content
         my_img1 = base64.b64encode(my_cnt1)
         my_img2 = base64.b64encode(my_cnt2)
         location_map.write(my_cnt1)
         location_sat.write(my_cnt2)
         location_map.close()
         location_sat.close()
   return [my_img1,my_img2]


# Logo for both dark mode and regular mode
def app_print_logo():
    if bool(DARK_MODE):
        print ('|image=iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAAAAXNSR0IArs4c6QAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAFU2lUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS40LjAiPgogICA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxuczpkYz0iaHR0cDovL3B1cmwub3JnL2RjL2VsZW1lbnRzLzEuMS8iCiAgICAgICAgICAgIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIgogICAgICAgICAgICB4bWxuczpzdFJlZj0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL3NUeXBlL1Jlc291cmNlUmVmIyIKICAgICAgICAgICAgeG1sbnM6dGlmZj0iaHR0cDovL25zLmFkb2JlLmNvbS90aWZmLzEuMC8iCiAgICAgICAgICAgIHhtbG5zOnhtcD0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wLyI+CiAgICAgICAgIDxkYzp0aXRsZT4KICAgICAgICAgICAgPHJkZjpBbHQ+CiAgICAgICAgICAgICAgIDxyZGY6bGkgeG1sOmxhbmc9IngtZGVmYXVsdCI+dGVzbGFfVF9CVzwvcmRmOmxpPgogICAgICAgICAgICA8L3JkZjpBbHQ+CiAgICAgICAgIDwvZGM6dGl0bGU+CiAgICAgICAgIDx4bXBNTTpEZXJpdmVkRnJvbSByZGY6cGFyc2VUeXBlPSJSZXNvdXJjZSI+CiAgICAgICAgICAgIDxzdFJlZjppbnN0YW5jZUlEPnhtcC5paWQ6NjFlOGM3OTktZDk2Mi00Y2JlLWFiNDItY2FmYjlmOTYxY2VlPC9zdFJlZjppbnN0YW5jZUlEPgogICAgICAgICAgICA8c3RSZWY6ZG9jdW1lbnRJRD54bXAuZGlkOjYxZThjNzk5LWQ5NjItNGNiZS1hYjQyLWNhZmI5Zjk2MWNlZTwvc3RSZWY6ZG9jdW1lbnRJRD4KICAgICAgICAgPC94bXBNTTpEZXJpdmVkRnJvbT4KICAgICAgICAgPHhtcE1NOkRvY3VtZW50SUQ+eG1wLmRpZDpCNkM1NEUzNDlERTAxMUU3QTRFNEExMTMwMUY5QkJBNTwveG1wTU06RG9jdW1lbnRJRD4KICAgICAgICAgPHhtcE1NOkluc3RhbmNlSUQ+eG1wLmlpZDpCNkM1NEUzMzlERTAxMUU3QTRFNEExMTMwMUY5QkJBNTwveG1wTU06SW5zdGFuY2VJRD4KICAgICAgICAgPHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD51dWlkOjI3MzY3NDg0MTg2QkRGMTE5NjZBQjM5RDc2MkZFOTlGPC94bXBNTTpPcmlnaW5hbERvY3VtZW50SUQ+CiAgICAgICAgIDx0aWZmOk9yaWVudGF0aW9uPjE8L3RpZmY6T3JpZW50YXRpb24+CiAgICAgICAgIDx4bXA6Q3JlYXRvclRvb2w+QWRvYmUgSWxsdXN0cmF0b3IgQ0MgMjAxNSAoTWFjaW50b3NoKTwveG1wOkNyZWF0b3JUb29sPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KI5WHQwAAANVJREFUOBHtU8ENwjAMTBADdJRuACMwUjdgBEaAEcoEgQlSJmCEcJYS6VzlYVfiV0snn6/na5SqIez17xuIvReUUi7QT8AInIFezRBfwDPG+OgZlIbQL5BrT7Xf0YcK4eJpz7LMKqQ3wDSJEViXBArWJd6pl6U0mORkVyADchUBXVXVRogZuAGDCrEOWExAq2TZO1hM8CzkY06yptbgN60xJ1lTa/BMa8xJ1tQavNAac5I30vblrOtHqxG+2eENnmD5fc3lCf6YU2H0BLtO7DnE7t12Az8xb74dVbfynwAAAABJRU5ErkJggg==')
    else:
        print ('|image=iVBORw0KGgoAAAANSUhEUgAAABYAAAAWCAYAAADEtGw7AAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAA/xpVFh0WE1MOmNvbS5hZG9iZS54bXAAAAAAADw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuMy1jMDExIDY2LjE0NTY2MSwgMjAxMi8wMi8wNi0xNDo1NjoyNyAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtbG5zOmRjPSJodHRwOi8vcHVybC5vcmcvZGMvZWxlbWVudHMvMS4xLyIgeG1wTU06T3JpZ2luYWxEb2N1bWVudElEPSJ1dWlkOjI3MzY3NDg0MTg2QkRGMTE5NjZBQjM5RDc2MkZFOTlGIiB4bXBNTTpEb2N1bWVudElEPSJ4bXAuZGlkOkI2QzU0RTM0OURFMDExRTdBNEU0QTExMzAxRjlCQkE1IiB4bXBNTTpJbnN0YW5jZUlEPSJ4bXAuaWlkOkI2QzU0RTMzOURFMDExRTdBNEU0QTExMzAxRjlCQkE1IiB4bXA6Q3JlYXRvclRvb2w9IkFkb2JlIElsbHVzdHJhdG9yIENDIDIwMTUgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDo2MWU4Yzc5OS1kOTYyLTRjYmUtYWI0Mi1jYWZiOWY5NjFjZWUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NjFlOGM3OTktZDk2Mi00Y2JlLWFiNDItY2FmYjlmOTYxY2VlIi8+IDxkYzp0aXRsZT4gPHJkZjpBbHQ+IDxyZGY6bGkgeG1sOmxhbmc9IngtZGVmYXVsdCI+dGVzbGFfVF9CVzwvcmRmOmxpPiA8L3JkZjpBbHQ+IDwvZGM6dGl0bGU+IDwvcmRmOkRlc2NyaXB0aW9uPiA8L3JkZjpSREY+IDwveDp4bXBtZXRhPiA8P3hwYWNrZXQgZW5kPSJyIj8+ux4+7QAAALlJREFUeNpi/P//PwMtABMDjcDQM5gFmyAjI2MAkLIHYgMgdsCh9wAQXwDig8B42oAhC4o8ZAwE74H4PpQ+D6XXA7EAFK9HkwOrxTAHi8ENUA3/0fB6KEYXB6ltIMZgkKv6oS4xgIqhGAYVM4CqmQ/SQ9BgbBjqbZjB54nRQ2yqeICDTXFyu4iDTbHBB3CwKTaY5KBgJLYQAmaa/9B0z0h2ziMiOKhq8AVaGfxwULiYcbQGobnBAAEGADCCwy7PWQ+qAAAAAElFTkSuQmCC')
    print('---')


# --------------------------
# The main function
# --------------------------

# The init function: Called to store your username and access_code in OS X Keychain on first launch
def init():
    # Here we do the setup
    # Store access_token in OS X keychain on first run
    print ('Enter your Cowboy username:')
    init_username = raw_input()
    print ('Enter your Cowboy password:')
    init_password = getpass.getpass()
    init_access_token = None

    try:
        c = TeslaConnection(init_username,init_password)
        init_password = ''
        init_access_token = c.get_token()
    except HTTPError as e:
        print ('Error contacting Cowboy servers. Try again later.')
        print e
        time.sleep(0.5)
        return
    except URLError as e:
        print ('Error: Unable to connect. Check your connection settings.')
        print e
        return
    except AttributeError as e:
        print ('Error: Could not get an access token from Cowboy. Try again later.')
        print e
        return
    keyring.set_password("mycowboy-bitbar","username",init_username)
    keyring.set_password("mycowboy-bitbar","access_token",init_access_token)



USERNAME = keyring.get_password("mycowboy-bitbar","username")  


# --------------------------
# The main function
# --------------------------

def main(argv):

    # CASE 1: init was called 
    if 'init' in argv:
       init()
       return
  

    # CASE 2: init was not called, keyring not initialized
    if DARK_MODE:
        color = '#FFDEDEDE'
        info_color = '#808080'
    else:
        color = 'black' 
        info_color = '#808080'

    USERNAME = keyring.get_password("mycowboy-bitbar","username")
    ACCESS_TOKEN = keyring.get_password("mycowboy-bitbar","access_token")
    
    if not USERNAME:   
       # restart in terminal calling init 
       app_print_logo()
       print ('Login to Cowboy | refresh=true terminal=true bash="\'%s\'" param1="%s" color=%s' % (sys.argv[0], 'init', color))
       return


# Further cleanup needed

    # CASE 3: init was not called, keyring initialized, no connection (access code not valid)
    try:
       # create connection to cowboy account
       # c = TeslaConnection(access_token = ACCESS_TOKEN)
       # vehicles = c.vehicles()
       # appointments = c.appointments()
    except: 
       app_print_logo()
       print ('Login to Cowboy | refresh=true terminal=true bash="\'%s\'" param1="%s" color=%s' % (sys.argv[0], 'init', color))
       return


    # CASE 4: all ok, specific command for a specific bike received
    if (len(sys.argv) > 1) and not('debug' in argv):
        # v = vehicles[int(sys.argv[1])]


        if sys.argv[2] == "wake_up":
            v.wake_up()
        else:
            if (len(sys.argv) == 2) and (sys.argv[2] != 'remote_start_drive'):
                # argv is of the form: CMD + vehicleid + command 
                # v.command(sys.argv[2])
            else:
                # argv is of the form: CMD + vehicleid + command + key:value pairs 
                # v.command(sys.argv[2],dict(map(lambda x: x.split(':'),sys.argv[3:])))
        return


    # CASE 5: all ok, all other cases
    app_print_logo()
    prefix = ''
    if len(vehicles) > 1:
        # Create a submenu for every bike
        prefix = '--'

    # loop through bikes, print menu with relevant info       
    for i, vehicle in enumerate(vehicles):

        if prefix:
           # print vehicle['display_name']

	try:
           # get the data for the vehicle       
           # vehicle_info = vehicle.vehicle_data() 
        except: 
           print ('%sError: Failed to get info from Cowboy. Click to try again. | refresh=true terminal=false bash="true" color=%s' % (prefix, color))
           return         

	vehicle_name = vehicle['display_name']
	vehicle_vin  = vehicle['vin'] 
       
        # add location & battery here

        distance_unit='km'  

        # if _LOCATION_TRACKING_: 
        #     locationdb.insert({'date':str(datetime.datetime.now()),'vehicle_info':vehicle_info})


        # --------------------------------------------------
        # DEBUG MENU
        # --------------------------------------------------

        if 'debug' in argv:
            # print ('>>> vehicle_info:\n%s\n'   % vehicle_info)
            # print ('>>> gui_settings:\n%s\n'   % gui_settings)
            # print ('>>> charge_state:\n%s\n'   % charge_state)
            # print ('>>> climate_state:\n%s\n'  % climate_state)
            # print ('>>> drive_state:\n%s\n'    % drive_state)
            # print ('>>> vehicle_state:\n%s\n'  % vehicle_state)
            # print ('>>> vehicle_config:\n%s\n' % vehicle_config)
            # print ('>>> appointments:\n%s\n'   % appointments)
            return


        # --------------------------------------------------
        # BATTERY MENU 
        # --------------------------------------------------

        print ('%sBattery:\t\t\t\t\t\t%s%% %s (%s %s) | color=%s' % (prefix, charge_state['battery_level'], cold_state(battery_loss_cold), battery_distance, distance_unit, color))
 
        print ('%s---' % prefix)


        # --------------------------------------------------
        # VEHICLE STATE MENU 
        # --------------------------------------------------

        print ('%sBike State:\t\t\t\t%s %s | color=%s' % (prefix, lock_state(vehicle_state['locked']), sentry_description, color))

        # Vehicle location overview

        gmaps = googleclient('AIzaSyCtVR6-HQOVMYVGG6vOxWvPxjeggFz39mg')
        car_location_address = gmaps.reverse_geocode((str(drive_state['latitude']),str(drive_state['longitude'])))[0]['formatted_address']

        print ('%s-----' % prefix)
        print ('%s--Address:\t\t%s| color=%s' % (prefix, car_location_address, color))
        print ('%s-----' % prefix)
        print ('%s--Lat:\t\t\t\t%s| color=%s' % (prefix, drive_state['latitude'], info_color))
        print ('%s--Lon:\t\t\t\t%s| color=%s' % (prefix, drive_state['longitude'], info_color))
        print ('%s--Heading:\t\t%s°| color=%s' % (prefix, drive_state['heading'], info_color))

        print ('%s---' % prefix)
        
        
        # --------------------------------------------------
        # VEHICLE MAP MENU 
        # --------------------------------------------------

        google_maps = retrieve_google_maps(str(drive_state['latitude']),str(drive_state['longitude']))
        vehicle_location_map = google_maps[0]
        vehicle_location_sat = google_maps[1]

        print ('%s|image=%s href="https://maps.google.com?q=%s,%s" color=%s' % (prefix, vehicle_location_map, drive_state['latitude'],drive_state['longitude'],color))
        print ('%s|image=%s alternate=true href="https://maps.google.com?q=%s,%s" color=%s' % (prefix, vehicle_location_sat, drive_state['latitude'],drive_state['longitude'],color))

        print ('%s---' % prefix)


if __name__ == '__main__':
    main(sys.argv)

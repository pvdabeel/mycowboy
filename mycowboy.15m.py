#!/usr/bin/env PYTHONIOENCODING=UTF-8 /usr/bin/python
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

import cowboy


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
    print ('|image=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')
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
        c = cowboy.Cowboy.with_auth(init_username,init_password)
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
    keyring.set_password("mycowboy-bitbar","password",init_password)
    init_password = ''



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

    if not USERNAME:   
       # restart in terminal calling init 
       app_print_logo()
       print ('Login to Cowboy | refresh=true terminal=true bash="\'%s\'" param1="%s" color=%s' % (sys.argv[0], 'init', color))
       return


    # CASE 3: init was not called, keyring initialized, no connection (access code not valid)
    try:
       True
       # create connection to cowboy account
       PASSWORD = keyring.get_password("mycowboy-bitbar","password")
       bike = cowboy.Cowboy.with_auth(USERNAME,PASSWORD)
       bike.refreshData()
    except: 
       app_print_logo()
       print ('Login to Cowboy | refresh=true terminal=true bash="\'%s\'" param1="%s" color=%s' % (sys.argv[0], 'init', color))
       return


    # CASE 4: all ok, specific command for a specific bike received
    # if (len(sys.argv) > 1) and not('debug' in argv):
    #    # v = vehicles[int(sys.argv[1])]
    #
    #
    #    if sys.argv[2] == "wake_up":
    #        v.wake_up()
    #    else:
    #        if (len(sys.argv) == 2) and (sys.argv[2] != 'remote_start_drive'):
    #            True
    #            # argv is of the form: CMD + vehicleid + command 
    #            # v.command(sys.argv[2])
    #        else:
    #            True
    #            # argv is of the form: CMD + vehicleid + command + key:value pairs 
    #            # v.command(sys.argv[2],dict(map(lambda x: x.split(':'),sys.argv[3:])))
    #    return


    # CASE 5: all ok, all other cases
    app_print_logo()
    prefix = ''

    try:

        bike_id       = bike.getBike().getId()
        bike_nickname = bike.getBike().getNickname()
	bike_firmware = bike.getBike().getFirmwareVersion()
        bike_position = bike.getBike().getPosition()
        bike_charge   = bike.getBike().getStateOfCharge()
        bike_distance = bike.getBike().getTotalDistance()
        bike_stolen   = bike.getBike().isStolen()

    except:
        return



    # add location & battery here

    distance_unit='km'  

    # if _LOCATION_TRACKING_: 
    #     locationdb.insert({'date':str(datetime.datetime.now()),'vehicle_info':vehicle_info})


    # --------------------------------------------------
    # DEBUG MENU
    # --------------------------------------------------

    if 'debug' in argv:
        print ('>>> id:\n%s\n'         % bike_id)
        print ('>>> nickname:\n%s\n'   % bike_nickname)
        print ('>>> firmware:\n%s\n'   % bike_firmware)
        print ('>>> position:\n%s\n'   % bike_position)
        print ('>>> charge:\n%s\n'     % bike_charge)
        print ('>>> distance:\n%s\n'   % bike_distance)
        print ('>>> stolen:\n%s\n'     % bike_stolen)
        return


    # --------------------------------------------------
    # MENU 
    # --------------------------------------------------

    print ('%sBike:\t\t\t\t\t\t\t%s | color=%s' % (prefix, bike_nickname, color))
    print ('%sBattery:\t\t\t\t\t\t\t%s%% | color=%s' % (prefix, bike_charge, color))
    print ('%s---' % prefix)

    print ('%sSerial:\t\t\t\t\t\t\t%s | color=%s' % (prefix, bike_id, info_color))
    print ('%sFirmware:\t\t\t\t\t\t%s | color=%s' % (prefix, bike_firmware, info_color))
    print ('%sSecurity:\t\t\t\t\t\tNot Stolen | color=%s' % (prefix, info_color))



    # --------------------------------------------------
    # LOCATION MENU 
    # --------------------------------------------------

    gmaps = googleclient('AIzaSyCtVR6-HQOVMYVGG6vOxWvPxjeggFz39mg')
    bike_location_address = gmaps.reverse_geocode((str(bike_position['latitude']),str(bike_position['longitude'])))[0]['formatted_address']

    print ('%s--Address:\t\t%s| color=%s' % (prefix, bike_location_address, color))
    print ('%s--Lat:\t\t\t\t%s| color=%s' % (prefix, bike_position['latitude'], info_color))
    print ('%s--Lon:\t\t\t\t%s| color=%s' % (prefix, bike_position['longitude'], info_color))
    print ('%s---' % prefix)
        
        
    # --------------------------------------------------
    # VEHICLE MAP MENU 
    # --------------------------------------------------

    google_maps = retrieve_google_maps(str(bike_position['latitude']),str(bike_position['longitude']))
    vehicle_location_map = google_maps[0]
    vehicle_location_sat = google_maps[1]

    print ('%s|image=%s href="https://maps.google.com?q=%s,%s" color=%s' % (prefix, vehicle_location_map, bike_position['latitude'],bike_position['longitude'],color))
    print ('%s|image=%s alternate=true href="https://maps.google.com?q=%s,%s" color=%s' % (prefix, vehicle_location_sat, bike_position['latitude'],bike_position['longitude'],color))

    print ('%s---' % prefix)


if __name__ == '__main__':
    main(sys.argv)

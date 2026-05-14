
# MyCowboy - MacOS Menubar plugin

Displays information regarding your Cowboy bike in the MacOS menubar. Allows you to remotely control your Cowboy bike as well.

![Imgur](https://i.imgur.com/Q45iFOP.png)


## Changelog: 

**Update 2021.11.02:**
- [X] Xbar compatible

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

## Installation instructions

1. Ensure you have [xbar](https://github.com/matryer/xbar/releases/latest) installed.
2. Install the Python deps:

   ```bash
   pip3 install requests tinydb keyring googlemaps
   ```

3. Copy [mycowboy.15m.py](mycowboy.15m.py) and the `library/` directory to your
   xbar plugins folder and `chmod +x` the script. (You can rename the file to
   change the refresh interval &mdash; e.g. `mycowboy.6h.py` for every six hours.)
4. Run xbar and click **"Login to Cowboy"**. The first-run flow stores your
   credentials in the macOS keychain and then prompts (optionally) for two
   Google API keys &mdash; see below.

## Google API keys

The plugin uses two Google APIs:

| Feature                       | API                                         | Where it's used                                  |
| ----------------------------- | ------------------------------------------- | ------------------------------------------------ |
| Inline map / satellite image  | **Maps Static API**                         | the two thumbnails under the location submenu    |
| Human-readable address        | **Geocoding API**                           | the "Address:" line under the location submenu   |

Both are **optional**. If neither key is configured the plugin still renders
bike + battery + location coordinates, just without the map and address.

### Getting keys

1. Open the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create (or pick) a project, then *Enable APIs*:
   - **Maps Static API**
   - **Geocoding API**
3. *Create Credentials &rarr; API key*. Two separate keys are recommended so
   each can be restricted to a single API:
   - Key 1: **API restriction** &rarr; *Maps Static API*
   - Key 2: **API restriction** &rarr; *Geocoding API*
4. Optionally add an **Application restriction** (e.g. your IP address).

### Configuring keys (three options)

The plugin reads keys in this order:
**environment variable &rarr; macOS keychain &rarr; not configured**.

#### Option A &mdash; from the menubar (recommended)

Click **Settings &rarr; Update Google API keys** in the menu. A terminal window
opens and prompts for each key (leave blank to keep the current value).
Internally this runs `mycowboy.15m.py keys`.

#### Option B &mdash; via the keychain directly

```bash
security add-generic-password -s mycowboy-bitbar -a google_static_key  -w 'YOUR_STATIC_MAPS_KEY' -U
security add-generic-password -s mycowboy-bitbar -a google_geocode_key -w 'YOUR_GEOCODING_KEY'   -U
```

Inspect or revoke later via *Keychain Access.app* (search for `mycowboy-bitbar`)
or:

```bash
security find-generic-password   -s mycowboy-bitbar -a google_static_key -w
security delete-generic-password -s mycowboy-bitbar -a google_static_key
```

#### Option C &mdash; via environment variables

Set these in your shell profile (or xbar's plugin environment):

```bash
export MYCOWBOY_GOOGLE_STATIC_KEY="YOUR_STATIC_MAPS_KEY"
export MYCOWBOY_GOOGLE_GEOCODE_KEY="YOUR_GEOCODING_KEY"
```

Environment variables override keychain values, which is handy for testing
without touching the keychain.

## Menubar settings

The bottom of the plugin menu exposes a **Settings** submenu:

- **Update Google API keys** &mdash; re-runs `mycowboy.15m.py keys` (Option A above).
- **Sign out & re-login** &mdash; re-runs `mycowboy.15m.py init` to refresh
  Cowboy credentials and (optionally) the Google keys.

## State locations

| Item                                                       | Location                                                   |
| ---------------------------------------------------------- | ---------------------------------------------------------- |
| Cowboy username / password                                 | macOS keychain (service `mycowboy-bitbar`)                 |
| Cached auth token                                          | macOS keychain (service `mycowboy-bitbar`, account `auth_token`) |
| Google Maps / Geocoding keys                               | macOS keychain (accounts `google_static_key`, `google_geocode_key`) |
| Location history                                           | `~/.state/mycowboy/mycowboy-locations.json` (TinyDB)       |
| Geocode cache                                              | `~/.state/mycowboy/mycowboy-geoloc.json` (TinyDB)          |
| Static map PNG cache (per rounded coordinate, per month)   | `~/.state/mycowboy/mycowboy-location-*.png`                |

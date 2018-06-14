# -*- coding: utf-8 -*-
"""
Created on Thu Nov 28 13:27:53 2013

@author: chipolux
"""
import re

import requests

class Steam:
    def __init__(self, api_key=None, version=2):
        self.__base_url = u'http://api.steampowered.com/'
        self.__key = api_key
        self.__version = 'v000%s' % version
    
    def get_apps(self):
        """Return a list of all app names and steam ids."""
        url =  self.__base_url + u'ISteamApps/GetAppList/' + self.__version
        store_url = u'http://store.steampowered.com/app/{appid}/'
        resp = requests.get(url)
        if not resp.ok:
            raise Exception('Failed to load applist %s: %s' % (resp.status_code, resp.url))
        try:
            data = resp.json()
        except:
            raise Exception('Unable to parse applist data.')
        try:
            apps = data['applist']['apps']
        except:
            raise Exception('Bad app data returned.')
        for app in apps:
            app['store_url'] = store_url.format(appid=app['appid'])
        return apps
    
    def get_store_app_details(self, appids):
        """Return store page details for app or list of apps."""
        if type(appids) == list:
            appids = [str(appid) for appid in appids]
        else:
            appids = [str(appids)]
        url = u'http://store.steampowered.com/api/appdetails/'
        resp = requests.get(url, params={'appids': ','.join(appids)})
        if not resp.ok:
            raise Exception('Failed to load store data %s: %s' % (resp.status_code, resp.url))
        try:
            data = resp.json()
        except:
            raise Exception('Unable to parse store data.')
        if not len(data.keys()) == len(appids):
            raise Exception('Failed to retrieve all app data.')
        app_data = {}
        for appid in appids:
            if not data[appid]['success']:
                app_data[appid] = {'success': False}
            else:
                app_data[appid] = data[appid]['data']
                app_data[appid]['success'] = True
        return app_data
    
    def get_store_pkg_details(self, pkgids):
        """Return store page details for pkg or list of pkgs."""
        pkgids = [str(pkgid) for pkgid in pkgids]
        url = u'http://store.steampowered.com/api/packagedetails/'
        resp = requests.get(url, params={'packageids': ','.join(pkgids)})
        if not resp.ok:
            raise Exception('Failed to load store data %s: %s' % (resp.status_code, resp.url))
        try:
            data = resp.json()
        except:
            raise Exception('Unable to parse store data.')
        if not len(data.keys()) == len(pkgids):
            raise Exception('Failed to retrieve all pkg data.')
        pkg_data = {}
        for pkgid in pkgids:
            if not data[pkgid]['success']:
                pkg_data[pkgid] = {'success': False}
            else:
                pkg_data[pkgid] = data[pkgid]['data']
                pkg_data[pkgid]['success'] = True
        return pkg_data
    
    def get_current_players(self, appid):
        """Return number of current players for app."""
        appid = str(appid)
        url =  self.__base_url + u'ISteamUserStats/GetNumberOfCurrentPlayers/v0001'
        resp = requests.get(url, params={'appid': appid})
        if not resp.ok:
            raise Exception('Failed to load current players %s: %s' % (resp.status_code, resp.url))
        try:
            data = resp.json()
        except:
            raise Exception('Unable to parse current player data.')
        data = data['response']
        if not data['result'] == 1:
            raise Exception('Current players not available via API.')
        return data['player_count']
    
    def get_frontpage_deals(self):
        """Return daily and flash deal app ids."""
        url = u'http://store.steampowered.com'
        resp = requests.get(url)
        if not resp.ok:
            raise Exception('Failed to load front page %s: %s' % (resp.status_code, resp.url))
        daily_start = resp.text.lower().find('daily deals')
        flash_start = resp.text.lower().find('flash sales', daily_start)
        flash_ends = []
        flash_ends.append(resp.text.lower().find('yesterday\'s big deals', flash_start))
        flash_ends.append(resp.text.lower().find('community\'s choice', flash_start))
        flash_ends.append(resp.text.lower().find('top sellers', flash_start))
        flash_ends = sorted(flash_ends)
        for flash_end in flash_ends:
            if flash_end > flash_start:
                break
        daily = resp.text[daily_start:flash_start]
        flash = resp.text[flash_start:flash_end]
        daily_deals = re.findall('http://store.steampowered.com/app/(\d*)/', daily)
        flash_sales = re.findall('http://store.steampowered.com/app/(\d*)/', flash)
        return daily_deals, flash_sales

if __name__ == '__main__':
    test = 'store_details'    
    
    # App List Test
    if test == 'app_list':
        steam = Steam()
        apps = steam.get_apps()
        print len(apps)
        print 'Test Done'
    
    # Store App Details Test
    if test == 'store_details':
        steam = Steam()
        appids = [241600]
        single_app = steam.get_store_app_details(appids)
        appids.extend([238320, 5])
        multi_app = steam.get_store_app_details(appids)
        print single_app.keys()
        print multi_app.keys()
        print 'Test Done'
    
    # Current Players Test
    if test == 'current_players':
        steam = Steam(version=1)
        appid = 241600
        current_players = steam.get_current_players(appid)
        print current_players
        print 'Test Done'
    
    # Frontpage Test
    if test == 'frontpage':
        steam = Steam()
        data = steam.get_frontpage()
        print data.keys()
        print 'Test Done'

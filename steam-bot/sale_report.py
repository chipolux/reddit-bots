# -*- coding: utf-8 -*-
"""
Created on Fri Aug 02 10:23:50 2013

@author: chipolux
"""
import datetime
import Queue
import time
import json
import os

import bot_utils as utils
import steam_api
import dropbox
import praw

# Function to updload file to dropbox
def upload_file(logger, file_path, access_token):
    try:
        client = dropbox.client.DropboxClient(access_token)
    except:
        logger.log_error('Unable to connect to dropbox.', 'dropbox')
        return False
    try:
        with open(file_path, 'rb') as f:
            client.put_file('/%s' % file_path, f)
            logger.log_debug('Uploaded file: %s' % file_path, 'dropbox')
            return True
    except:
        logger.log_error('Unable to upload file.', 'dropbox')
        return False

# Function to wrap get_json_response for threaded use
def get_apps_info(steam, queue, apps, daily_deals, flash_deals):
    appids = [str(app['appid']) for app in apps]
    try:
        data = steam.get_store_app_details(appids)
    except:
        data = {}
    # Parse out store data we want
    del_list = []
    for i, appid in enumerate(appids):
        # Check if there is any data for app
        if not data.has_key(appid):
            del_list.append(i)
            continue
        # Check if API returned data for app
        if not data[appid]['success']:
            del_list.append(i)
            continue
        # Check if app is DLC
        if data[appid].has_key('fullgame'):
            del_list.append(i)
            continue
        # Get price data
        if data[appid].has_key('price_overview'):
            apps[i][u'price'] = data[appid]['price_overview'].get('final', 0)
            apps[i][u'discount'] = data[appid]['price_overview'].get('discount_percent', 0)
        else:
            del_list.append(i)
            continue
        # Get metacritic score
        if data[appid].has_key('metacritic'):
            apps[i][u'score'] = data[appid]['metacritic'].get('score', 'N/A')
            apps[i][u'score_url'] = data[appid]['metacritic'].get('url', 'N/A')
        else:
            apps[i][u'score'] = 'N/A'
            apps[i][u'score_url'] = 'N/A'
        # Get recommendations
        if data[appid].has_key('recommendations'):
            apps[i][u'recommendations'] = data[appid]['recommendations'].get('total', 0)
        else:
            apps[i][u'recommendations'] = 0
        # Get release date
        if data[appid].has_key('release_date'):
            apps[i][u'release_date'] = data[appid]['release_date'].get('date', 'N/A')
        else:
            apps[i][u'release_date'] = 'N/A'
        # Get platform support
        if data[appid].has_key('platforms'):
            apps[i][u'win_support'] = data[appid]['platforms'].get('windows', False)
            apps[i][u'mac_support'] = data[appid]['platforms'].get('mac', False)
            apps[i][u'nix_support'] = data[appid]['platforms'].get('linux', False)
        else:
            del_list.append(i)
            continue
        # Get trading cards
        try:
            apps[i][u'trading_cards'] = False
            for category in data[appid]['categories']:
                if str(category['id']) == '29':
                    apps[i][u'trading_cards'] = True
        except KeyError:
            apps[i][u'trading_cards'] = False
    # Mark daily and flash deals
    for i, appid in enumerate(appids):
        if appid in daily_deals:
            apps[i][u'daily_deal'] = True
        else:
            apps[i][u'daily_deal'] = False
        if appid in flash_deals:
            apps[i][u'flash_deal'] = True
        else:
            apps[i][u'flash_deal'] = False
    # Remove apps marked for deletion
    del_list.reverse()
    for i in del_list:
        del(apps[i])
        del(appids[i])
    # Retrieve current players for apps
    for i, appid in enumerate(appids):
        try:
            current_players = steam.get_current_players(appid)
        except:
            logger.log_error('Failed to load current players: %s' % appid)
            current_players = 0
        apps[i][u'active_players'] = current_players
    # Send app dicts down the pipeline
    for app in apps:
        queue.put(app)
    return apps

# Function to collate data from threads
def get_data(queue):
    apps = []
    while True:
        try:
            data = queue.get_nowait()
        except Queue.Empty:
            continue
        if data == 'EXIT':
            queue.task_done()
            break
        apps.append(data)
    return apps

# Function to format app data into reddit message body
def format_data(apps):
    body = (u'Game|Price|Disc.|Released|W|M|L|TC|MCritic|Charts|Wiki\n'
            u':-|-:|-:|:-|:-:|:-:|:-:|:-:|-:|-:|-:\n')
    template = (u'{name}|{price}|{discount}|{release_date}|{win}|{mac}|{nix}|'
                u'{tc}|{metacritic}|{steamcharts}|{wiki}\n')
    if len(apps) < 1:
        return u'No Items To Display|\n:\n'
    for app in apps:
        charts_url = u'http://steamcharts.com/app/%s' % app['appid']
        charts_link = u'[SteamCharts](%s)' % charts_url
        wiki_url = u'http://pcgamingwiki.com/appid.php?appid=%s' % app['appid']
        wiki_link = u'[Wiki](%s)' % wiki_url
        if app['score'] == 'N/A':
            meta_link = u'N/A'
        else:
            meta_link = u'[%s](%s)' % (app['score'], app['score_url'])
        if len(app['name']) > 35:
            name = '%s...' % app['name'][0:32]
        else:
            name = app['name']
        if app['win_support']:
            win = 'W'
        else:
            win = ''
        if app['mac_support']:
            mac = 'M'
        else:
            mac = ''
        if app['nix_support']:
            nix = 'L'
        else:
            nix = ''
        if mac or nix:
            name = '**%s**' % name
        if app['trading_cards']:
            tc = u'\u2713'
        else:
            tc = ''
        body += template.format(name = '[%s](%s)' % (name, app['store_url']),
                                price = '$%.2f' % (app['price'] * .01),
                                discount = '%d%%' % app['discount'],
                                release_date = app['release_date'],
                                win = win,
                                mac = mac,
                                nix = nix,
                                metacritic = meta_link,
                                steamcharts = charts_link,
                                wiki = wiki_link,
                                tc = tc)
    return body

# Fetch all store API data
def fetch_store_data(steam, queue, logger, applist):
    # Get deal lists
    try:
        daily_deals, flash_deals = steam.get_frontpage_deals()
    except:
        logger.log_error('Failed to load frontpage data.', 'steam')
        daily_deals = []
        flash_deals = []
    # Start getting app data in threads
    thread_holder = []
    apps_left = True
    while apps_left:
        # Prep list of apps for thread
        apps = []
        for i in range(5):
            try:
                apps.append(applist.pop())
            except IndexError:
                apps_left = False
                break
        # Wait until less than 100 threads are running
        while True:
            thread_lives = [x.is_alive() for x in thread_holder]
            if thread_lives.count(True) < 100:
                break
        # Clean up closed threads
        del_list = []
        thread_lives = [x.is_alive() for x in thread_holder]
        for i in xrange(len(thread_lives)):
            if not thread_lives[i]:
                del_list.append(i)
        del_list.reverse()
        for i in del_list:
            del(thread_holder[i])
        # Kick off new thread
        try:
            thread_holder.append(utils.GenericThread(get_apps_info, steam, queue,
                                                     apps, daily_deals, flash_deals))
            thread_holder[-1].start()
        except:
            logger.log_error('Unable to start thread: %s' % apps, 'processing')
            continue
    # Wait for all threads to close
    while True:
        thread_lives = [x.is_alive() for x in thread_holder]
        if thread_lives.count(True) == 0:
            queue.put('EXIT')
            break
    return True

# Function to build post text
def build_post(apps):
    # Build breakdown portion
    post_title = 'Steam Sale Report - %s' % datetime.datetime.utcnow().strftime('%Y-%m-%d @ %H:00 UTC')
    post_body = (u'###General Breakdown\n'
                 u'Criteria|Result\n'
                 u':-|-:\n'
                 u'Total On Sale Apps|{total}\n')
    breakdown = {'total': len(apps)}
    post_body = post_body.format(**breakdown)
    
    # Build daily deals portion
    post_body = u'###***Current Daily Deals***\n---\n'
    daily_list = []
    for app in apps:
        if app['daily_deal']:
            daily_list.append(app)
    post_body += format_data(daily_list)
    
    # Build flash deals portion
    post_body += u'###***Current Flash Deals***\n---\n'
    flash_list = []
    for app in apps:
        if app['flash_deal']:
            flash_list.append(app)
    post_body += format_data(flash_list)
    
    # Remove bad apps
    del_list = []
    for i in xrange(len(apps)):
        if str(apps[i]['appid']) in settings['steam']['excluded_apps']:
            del_list.append(i)
    del_list.reverse()
    for i in del_list:
        del(apps[i])
    
    # Build ranked portion
    post_body += u'###***Top 20 On Sale Apps***\n---\n'
    calculate_ranks(apps)
    apps = sorted(apps, key=lambda x: x['rank'], reverse=True)
    post_body += format_data(apps[0:20])
    
    # Build key portion
    post_body += (u'###***Key***\n---\n'
                  u'Header|Definition\n'
                  u':-|:-\n'
                  u'Game|Game Title\n'
                  u'Price|Current Price in USD\n'
                  u'Disc.|Discount Percent\n'
                  u'Released|Steam Release Date\n'
                  u'W|Windows Support\n'
                  u'M|Mac Support\n'
                  u'L|Linux Support\n'
                  u'TC|Trading Cards Available\n'
                  u'MCritic|Metacritic Score\n'
                  u'Charts|Link To SteamCharts\n'
                  u'Wiki|Link To PCGamingWiki\n'
                  u'**Bold**|Mac Or Linux Support\n')
    
    # Append tail info
    post_body += (u'###[Get Full Sale Reports Here In JSON Format]'
                  u'(https://www.dropbox.com/sh/ttiutlhjujtc83m/WXrj85A_Jl)\n\n'
                  u'^This ^post ^was ^made ^by ^a ^bot.\n\n'
                  u'^Please ^contact ^[{owner}]'
                  u'(http://www.reddit.com/message/compose?to={owner}&subject=Steam%20Bot%20Question)'
                  u' ^for ^details.\n\n').format(owner = settings['reddit']['owner'])
    return post_title, post_body

# Function to calculate app rank
def calculate_ranks(apps):
    total_players = float(sum([x['active_players'] for x in apps])) or 1.0
    total_recommendations = float(sum([x['recommendations'] for x in apps])) or 1.0
    for app in apps:
        if not app.has_key('rank'):
            app['rank'] = 0
        # Metacritic Rank
        if app['score'] == 'N/A':
            app['rank'] += 0
        else:
            app['rank'] += round(int(app['score'])/40.0, 2)
        # Players Rank
        app['rank'] += round((int(app['active_players'])/total_players)*25, 2)
        # Recommendations Rank
        app['rank'] += round((int(app['recommendations'])/total_recommendations)*15, 2)

# Write app data out to file
def write_report(logger, apps, path):
    try:
        with open(path, 'w') as f:
            json.dump(apps, f, indent=4, separators=(',', ': '))
        logger.log_debug('Wrote app data to file.', 'data_export')
    except:
        logger.log_error('Unable to write app data to file.', 'data_export')

# Submit post to subreddits
def submit_post(logger, subreddits, title, body):
    results = []
    for sub_name in subreddits:
        try:
            subreddit = reddit.get_subreddit(sub_name)
        except:
            logger.log_error('Unable to connect to subreddit: %s' % sub_name, 'reddit')
            continue
        try:
            logger.log_debug('Submitting post to %s' % sub_name, 'reddit')
            result = subreddit.submit(title, body)
            results.append(result)
        except:
            logger.log_error('Unable to submit to reddit: %s' % sub_name, 'reddit')
            continue
    return results

# Write new posts
def write_new_posts(logger, subreddits, new_posts):
    # Load old posts
    try:
        with open('old_posts.json', 'r') as f:
            old_posts = json.load(f)
            logger.log_debug('Old posts loaded.', 'data_import')
    except IOError:
        old_posts = None
        logger.log_debug('No old posts found.', 'data_import')
    # Build new posts data
    posts = {}
    for i, subreddit in enumerate(subreddits):
        posts[subreddit] = new_posts[i].id
    # Write new posts
    try:
        with open('old_posts.json', 'w') as f:
            json.dump(posts, f, indent=4, separators=(',', ': '))
            logger.log_debug('Wrote new post ids.', 'data_export')
    except IOError:
        logger.log_error('Unable to write new post ids.', 'data_export')
    return old_posts

# Remove old posts
def remove_old_posts(logger, subreddits, old_posts):
    # Delete old posts
    if old_posts == None:
        return True
    for subreddit in subreddits:
        if not old_posts.has_key(subreddit):
            continue
        try:
            post = reddit.get_submission(submission_id=old_posts[subreddit])
            logger.log_debug('Loaded last post.', 'reddit')
        except:
            logger.log_error('Unable to load last post.', 'reddit')
            continue
        try:
            post.delete()
            logger.log_debug('Deleted last post.', 'reddit')
        except:
            logger.log_error('Unable to delete last post.', 'reddit')
            continue
    return True

if __name__ == '__main__':
    # Load settings
    with open('settings.json', 'r') as f:
        settings = json.load(f)
    
    # Create logger
    logger = utils.Logger(path=settings['logging']['path'],
                          handle=settings['logging']['handle'],
                          level=settings['logging']['level'],
                          rotation=settings['logging']['rotation'],
                          remote=settings['logging']['remote'],
                          url=settings['logging']['url'],
                          key=settings['logging']['key'])
    
    # Initialize reddit
    try:
        reddit = praw.Reddit(user_agent=settings['reddit']['agent'])
        reddit.login(settings['reddit']['username'], settings['reddit']['password'])
    except:
        logger.log_error('Unable to connect to reddit.', 'reddit')
        utils.safe_exit(logger)
    
    # Initialize Steam
    steam = steam_api.Steam()
    
    # Set up queues
    store_data_queue = Queue.Queue()
    
    # Get app list
    logger.log_debug('Loading app list.', 'steam')
    try:
        apps = steam.get_apps()
    except:
        logger.log_error('Unable to load app list.', 'steam')
        utils.safe_exit(logger)
    
    # Start threads to get all store data
    fetch_store_data(steam, store_data_queue, logger, apps)
    
    # Fetch all data out of queue and remove non-sale apps
    apps = get_data(store_data_queue)
    apps = filter(lambda x: x['discount'] > 0, apps)
    
    # Build post
    title, body = build_post(apps)
    
    # Do reports
    path = 'Report_%s.json' % datetime.datetime.utcnow().strftime('%Y-%m-%d-%H')
    write_report(logger, apps, path)
    if os.path.exists(path) and settings['dropbox']['enabled']:
        upload_file(logger, path, settings['dropbox']['token'])
    
    # Submit to reddit
    results = submit_post(logger, settings['reddit']['subreddits'], title, body)
    
    # Write new posts
    old_posts = write_new_posts(logger, settings['reddit']['subreddits'], results)
    
    # Remove old posts
    if settings['reddit']['remove_old_posts']:
        remove_old_posts(logger, settings['reddit']['subreddits'], old_posts)

# -*- coding: utf-8 -*-
"""
Created on Sun Jan 12 21:00 2014

@author: chipolux
"""
import json
import os

import bot_utils as utils
import requests
import praw

# Main function
def main():
    # Load settings
    settings = load_json('settings.json')
    # Create logger
    logger = utils.Logger(**settings['logging'])
    # Load reddit
    try:
        logger.log_debug('Connecting to reddit.', 'reddit')
        reddit = get_reddit(settings['reddit']['username'],
                            settings['reddit']['password'],
                            settings['reddit']['useragent'])
    except:
        logger.log_error('Unable to connect to reddit.', 'reddit')
        utils.safe_exit()
    # Load/Create state file
    logger.log_debug('Loading state file.', 'process')
    if os.path.exists('state.json'):
        with open('state.json', 'r') as f:
            state = json.load(f)
    else:
        logger.log_debug('No state file, setting up blank.', 'process')
        state = dict([(s, {}) for s in settings['reddit']['subreddits']])
    # Load subreddits
    for subreddit_name in settings['reddit']['subreddits']:
        logger.log_debug('Processing subreddit: %s' % subreddit_name, 'process')
        try:
            logger.log_debug('Connecting to subreddit: %s' % subreddit_name, 'process')
            subreddit = reddit.get_subreddit(subreddit_name)
        except:
            logger.log_error('Unable to connect to subreddit: %s' % subreddit_name, 'reddit')
            continue
        # Load subreddit specific settings
        try:
            logger.log_debug('Loading config page: %s' % subreddit_name, 'process')
            page = subreddit.get_wiki_page('twitch_bot')
        except praw.requests.HTTPError:
            logger.log_error('No settings page for subreddit: %s' % subreddit_name, 'reddit')
            continue
        try:
            logger.log_debug('Parsing config page data: %s' % subreddit_name, 'process')
            channels = json.loads(page.content_md)
        except:
            logger.log_error('Unable to parse settings page: %s' % subreddit_name, 'reddit')
            continue
        # Remove old channels
        needs_update = False
        logger.log_debug('Cleaning out old channels.', 'process')
        for channel in state[subreddit_name].keys():
            if not channel in channels:
                del(state[subreddit_name][channel])
                needs_update = True
        # Check channel status
        logger.log_debug('Begin checking channel status.', 'process')
        for channel in channels:
            logger.log_debug('Checking channel: %s' % channel, 'process')
            try:
                status = check_stream(channel)
            except:
                logger.log_error('Failed to check channel: %s' % channel, 'twitch')
                status = False
            if not state[subreddit_name].has_key(channel):
                state[subreddit_name][channel] = None
            if state[subreddit_name][channel] != status:
                state[subreddit_name][channel] = status
                needs_update = True
        if not needs_update:
            logger.log_debug('No sidebar update required: %s' % subreddit_name, 'process')
            continue
        # Update sidebar
        try:
            logger.log_info('Updating sidebar: %s' % subreddit_name, 'process')
            set_sidebar(subreddit,
                        [(c, state[subreddit_name][c]) for c in state[subreddit_name].keys()],
                        settings['reddit']['owner'])
        except:
            logger.log_error('Unable to update sidebar: %s' % subreddit_name, 'reddit')
            continue
    # Processing complete, save state
    try:
        logger.log_debug('Writing state.', 'process')
        write_json('state.json', state)
    except:
        logger.log_error('Failed to write state file.', 'process')
    utils.safe_exit()

# Load reddit function
def get_reddit(username, password, useragent):
    reddit = praw.Reddit(user_agent=useragent)
    reddit.login(username, password)
    return reddit

# Set sidebar status
def set_sidebar(subreddit, channels, bot_owner):
    section = u'[](/BEGINTWITCH)\n\nChannel|Status\n:|:\n'
    template = u'[{channel}](http://www.twitch.tv/{channel})|{status}\n'
    footer = (u'^This ^section ^created ^automatically.\n'
              u'^Contact ^[{owner}]'
              u'(http://www.reddit.com/message/compose?to={owner}&subject=Twitch%20Bot) '
              u'^for ^details.\n'
              u'[](/ENDTWITCH)').format(owner=bot_owner)
    for channel in sorted(channels, key=lambda x: x[0]):
        name = channel[0]
        if channel[1]:
            status = 'LIVE'
        else:
            status = 'OFFLINE'
        section += template.format(channel=name, status=status)
    section += footer
    page = subreddit.get_wiki_page('config/sidebar')
    start = page.content_md.lower().find('[](/begintwitch)')
    end = page.content_md.lower().find('[](/endtwitch)') + 14
    if not start < end:
        raise Exception('Sidebar does not have bot section.')
    new_content = page.content_md[:start] + section + page.content_md[end:]
    page.edit(new_content)

# Check if stream online
def check_stream(channel):
    url = u'https://api.twitch.tv/kraken/streams/%s' % channel
    headers = {'accept': 'application/vnd.twitchtv.v2+json'}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    if data['stream']:
        return True
    else:
        return False

# JSON Functions
def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4, separators=(',', ': '))

def load_json(path):
    with open(path, 'r') as f:
        data = json.load(f)
    return data

if __name__ == '__main__':
    main()

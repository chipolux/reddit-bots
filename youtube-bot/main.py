# -*- coding: utf-8 -*-

import praw
import requests
import bot_utils as utils

import json
import sys


def post_videos():
    settings, logger = initialize()

    # Initialize reddit
    try:
        logger.log_debug('Initializing reddit.', 'reddit')
        reddit = praw.Reddit(user_agent=settings['reddit']['user_agent'])
        reddit.login(
            settings['reddit']['username'], settings['reddit']['password'])
        logger.log_debug('Initialized reddit.', 'reddit')
    except Exception as e:
        logger.log_error('Unable to connect to reddit: %s' % e, 'reddit')
        return 1

    # Connect to subreddit
    try:
        logger.log_debug('Grabbing subreddit.', 'reddit')
        subreddit = reddit.get_subreddit(settings['reddit']['subreddit'])
        logger.log_debug('Grabbed subreddit.', 'reddit')
    except Exception as e:
        logger.log_error('Unable to connect to subreddit: %s' % e, 'reddit')
        return 1

    # Check if channel id in settings, load if not
    if 'id' not in settings['youtube']:
        # Load channel id
        try:
            logger.log_debug('Loading channel id.', 'youtube')
            settings['youtube']['id'] = get_channel_id(
                settings['youtube']['channel'], settings['youtube']['api_key'])
        except Exception as e:
            logger.log_error('Failed to load channel id: %s' % e, 'youtube')
            return 1

        # Write settings with channel id
        try:
            logger.log_debug('Writing settings with channel id.', 'io')
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4, separators=(',', ': '))
        except Exception as e:
            logger.log_error('Failed to write settings: %s' % e, 'io')
            return 1

    # Fetch recent videos
    try:
        logger.log_debug('Fetching new videos.', 'youtube')
        settings['youtube'].setdefault('after', None)
        videos = get_videos(settings['youtube']['id'],
                            settings['youtube']['api_key'],
                            settings['youtube']['after'])
    except Exception as e:
        logger.log_error('Failed to load videos: %s' % e, 'youtube')
        return 1

    # Check if any new videos
    if len(videos) == 0:
        logger.log_debug('No new videos to post.', 'process')
        return 0

    # Load old post titles
    try:
        logger.log_debug('Loading old post titles.', 'reddit')
        posts = reddit.user.get_submitted(limit=150)
        posted_titles = [p.title for p in posts]
    except Exception as e:
        logger.log_error('Unable to load posts: %s' % e, 'reddit')
        return 1

    # Remove previously posted videos
    logger.log_debug('Removing previously posted videos.', 'process')
    for i, video in enumerate(videos):
        if video['title'] in posted_titles:
            logger.log_debug('%s Already Posted.' % video['id'], 'reddit')
            videos[i] = None
    while videos.count(None):
        videos.remove(None)

    # Check if any new videos
    if len(videos) == 0:
        logger.log_debug('No new videos to post.', 'process')
        return 0
    elif len(videos) >= 5:
        logger.log_error('Too many videos to post, please advise.', 'process')
        return 1

    # Post new videos
    videos.reverse()
    for video in videos:
        post = None
        try:
            logger.log_debug('Posting Video: %s' % video['id'], 'reddit')
            post = subreddit.submit(video['title'], url=video['url'])
            logger.log_info('Posted Video: %s' % video['id'], 'reddit')
        except praw.errors.AlreadySubmitted:
            logger.log_info('Already Posted: %s' % video['id'], 'reddit')
        except Exception as e:
            logger.log_error(
                'Unable To Post (%s): %s' % (video['id'], e), 'reddit')
            return 1

        if settings['reddit'].get('auto_approve', False) and post:
            try:
                logger.log_debug('Approving Post: %s' % post.id)
                post.approve()
                logger.log_info('Appoved Post: %s' % post.id)
            except:
                logger.log_error('Unable to approve post: %s' % post.id)
                return 1

    # Write settings if date updated
    if not settings['youtube']['after'] == video['date']:
        logger.log_debug('Writing settings to file.', 'io')
        settings['youtube']['after'] = video['date']
        while True:
            try:
                with open('settings.json', 'w') as f:
                    json.dump(settings, f, indent=4, separators=(',', ': '))
                break
            except Exception as e:
                logger.log_error('Failed to write settings: %s' % e, 'io')
                return 1

    # Exit
    return 0


def initialize():
    # Load settings
    with open('settings.json', 'r') as f:
        settings = json.load(f)

    # Create logger
    logger = utils.Logger(**settings['logging'])

    # Return components
    return settings, logger


def get_channel_id(user, api_key):
    url = u'https://www.googleapis.com/youtube/v3/channels'
    params = {'key': api_key, 'part': 'id', 'forUsername': user}
    resp = requests.get(url, params=params)
    if not resp.ok:
        raise Exception('Unable to load channel id!')
    return resp.json()['items'][0]['id']


def get_videos(channel_id, api_key, after=None, limit=10):
    url = u'https://www.googleapis.com/youtube/v3/search'
    params = {
        'key': api_key,
        'part': 'snippet',
        'channelId': channel_id,
        'maxResults': limit,
        'type': 'video',
        'order': 'date',
        'safeSearch': 'none'}
    if after:
        params['publishedAfter'] = after
    resp = requests.get(url, params=params)
    if not resp.ok:
        raise Exception('Unable to load videos: %s' % resp)
    base_url = u'https://www.youtube.com/watch?v={id}'
    videos = []
    for video in resp.json()['items']:
        if video['snippet']['publishedAt'] == after:
            break
        videos.append({'id': video['id']['videoId'],
                       'title': video['snippet']['title'],
                       'url': base_url.format(id=video['id']['videoId']),
                       'date': video['snippet']['publishedAt']})
    return videos


if __name__ == '__main__':
    sys.exit(post_videos())

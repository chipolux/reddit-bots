# -*- coding: utf-8 -*-
"""
Created on Fri Apr 04 19:00:00 2014

@author: chipolux
"""
import json
import sys

from BeautifulSoup import BeautifulSoup
import praw
import requests

import bot_utils as utils


def main():
    # Initialize core components
    settings, logger, posted_videos = initialize_core()

    # Initialize reddit components
    reddit, subreddit = initialize_reddit(
        settings['reddit']['username'],
        settings['reddit']['password'],
        settings['reddit']['user_agent'],
        settings['reddit']['subreddit'],
        logger
    )

    # Load videos from site
    videos = load_videos(settings['tag'], logger)

    # Filter out known videos
    videos = filter_known_videos(videos, posted_videos, logger)

    # Exit if no new videos
    if len(videos) == 0:
        logger.log_debug('No videos to post.', 'site')
        return 0

    # Remove videos already posted to reddit
    videos = filter_posted_videos(videos, posted_videos, reddit, logger)

    # Prevent video flood
    if len(videos) > 2:
        logger.log_error('Too many videos.', 'site')
        return 1
    elif len(videos) == 0:
        write_videos(posted_videos, logger)
        logger.log_debug('No videos to post.', 'site')
        return 0

    # Post videos
    post_videos(videos, posted_videos, subreddit, logger)

    # Write posted videos
    write_videos(posted_videos, logger)

    # Exit
    return 1


def initialize_core():
    # Load settings
    with open('settings.json', 'r') as f:
        settings = json.load(f)

    # Create logger
    logger = utils.Logger(**settings['logging'])

    # Load posted videos
    try:
        with open('posted_videos.json', 'r') as f:
            posted_videos = json.load(f)
            logger.log_debug(
                'Loaded Old Videos: %s' % len(posted_videos),
                'data_import'
            )
    except IOError:
        posted_videos = []
        logger.log_debug('No old videos.', 'data_import')

    # Return components
    return settings, logger, posted_videos


def initialize_reddit(username, password, user_agent, subreddit, logger):
    # Initialize reddit
    try:
        reddit = praw.Reddit(user_agent=user_agent)
        reddit.login(username, password)
    except:
        logger.log_error('Unable to connect to reddit.', 'reddit')
        sys.exit(1)

    # Connect to subreddit
    try:
        subreddit = reddit.get_subreddit(subreddit)
    except:
        logger.log_error('Unable to connect to subreddit.', 'reddit')
        sys.exit(1)
    return reddit, subreddit


def load_videos(tag, logger):
    url = 'http://www.yogscast.com/ajax/browse/family/tag/%s' % tag
    resp = requests.get(url)
    if not resp.ok:
        logger.log_error('Could not load tag page!', 'site')
        sys.exit(1)
    page = BeautifulSoup(
        resp.text,
        convertEntities=BeautifulSoup.ALL_ENTITIES
    )
    video_list = page.find('article', {'id': 'latest'}).find('ul')
    videos = []
    for video in video_list.findAll('figure', recursive=True):
        if video.has_key('data-code'):
            videos.append(load_video(video['data-code'], logger))
    logger.log_debug('Loaded Site Videos: %s' % len(videos), 'site')
    return videos


def load_video(video_code, logger):
    base_url = 'http://www.yogscast.com/'
    ajax_url = base_url + 'ajax/video/%s' % video_code
    video_url = base_url + 'video/%s' % video_code
    resp = requests.get(ajax_url)
    if not resp.ok:
        logger.log_error('Could not load video page: %s' % video_code, 'site')
        sys.exit(1)
    page = BeautifulSoup(
        resp.text,
        convertEntities=BeautifulSoup.ALL_ENTITIES
    )
    video_data = page.find('div', {'id': 'video-json-data'})
    video_data = json.loads(video_data.text)
    return {'title': video_data['title'], 'code': video_code,
            'library': video_data['library_id'], 'url': video_url}


def filter_known_videos(videos, posted_videos, logger):
    new_videos = []
    skipped = 0
    for video in videos:
        if video['code'] in posted_videos:
            logger.log_debug('%s Already Posted.' % video['code'], 'logic')
            skipped += 1
        else:
            new_videos.append(video)
    logger.log_debug('Skipped %s Known Videos.' % skipped, 'logic')
    return new_videos


def filter_posted_videos(videos, posted_videos, reddit, logger):
    # Load old post titles
    logger.log_debug('Loading old post titles.', 'reddit')
    try:
        posts = reddit.user.get_submitted(limit=150)
        posted_titles = [p.title for p in posts]
    except Exception as e:
        logger.log_error('Unable To Load Posts: %s' % e, 'reddit')
        sys.exit(1)

    # Record videos alread posted to reddit and yield others
    new_videos = []
    skipped = 0
    for video in videos:
        if video['title'] in posted_titles:
            logger.log_debug('%s Already Posted.' % video['code'], 'reddit')
            posted_videos.append(video['code'])
            skipped += 1
        else:
            new_videos.append(video)
    logger.log_debug('Skipped %s Posted Videos.' % skipped, 'logic')
    return new_videos


def post_videos(videos, posted_videos, subreddit, logger):
    videos.reverse()
    for video in videos:
        logger.log_info('Posting Video: %s' % video['code'], 'reddit')
        try:
            subreddit.submit(video['title'], url=video['url'])
            posted_videos.append(video['code'])
        except:
            logger.log_error('Unable To Post: %s' % video['code'], 'reddit')
            sys.exit(1)


def write_videos(posted_videos, logger):
    posted_videos = list(set(posted_videos))
    logger.log_debug(
        'Writing posted videos: %s' % len(posted_videos),
        'data_export'
    )
    try:
        with open('posted_videos.json', 'w') as f:
            json.dump(posted_videos, f, indent=4, separators=(',', ': '))
    except:
        logger.log_error(
            'Unable to write posted videos: %s' % len(posted_videos),
            'data_export'
        )
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())

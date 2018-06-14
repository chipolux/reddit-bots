'''
Yogscast Video Thread Bot

Created By: chipolux
'''
import os
import copy
import json
import time
import datetime

import praw
import requests
import bot_utils as utils

def main():
    settings, logger, reddit, subreddit = initialize()
    loop(settings, logger, reddit, subreddit)

def initialize():
    # Initialization Loop
    while True:
        # Load settings
        try:
            settings = utils.load_json('settings.json')
        except:
            print 'Error loading settings!'
            time.sleep(15)
            continue

        # Create logger
        try:
            logger = utils.Logger(**settings['logging'])
        except:
            print 'Error initializing logger!'
            time.sleep(15)
            continue

        # Load reddit
        try:
            logger.log_debug('Connecting to reddit.', 'reddit')
            reddit = praw.Reddit(user_agent=settings['reddit']['useragent'])
            reddit.login(settings['reddit']['username'],
                         settings['reddit']['password'])
        except:
            logger.log_error('Unable to connect to reddit.', 'reddit')
            time.sleep(15)
            continue

        # Load subreddit
        try:
            logger.log_debug('Loading subreddit.', 'reddit')
            subreddit = reddit.get_subreddit(settings['reddit']['subreddit'])
        except:
            logger.log_error('Unable to connect to subreddit.', 'reddit')
            time.sleep(15)
            continue
        break
    return settings, logger, reddit, subreddit

def loop(settings, logger, reddit, subreddit):
    # Load state if stored in file
    if os.path.exists('state.json'):
        state = utils.load_json('state.json')
    else:
        state = {}

    # Start main loop
    while True:
        try:
            # Make copy of state for write determination
            old_state = copy.deepcopy(state)

            # Load config page
            try:
                logger.log_debug('Loading config page.', 'reddit')
                page = subreddit.get_wiki_page('youtube_bot')
            except:
                logger.log_error('Unable to load config page.', 'reddit')
                time.sleep(15)
                continue

            # Parse config page
            try:
                logger.log_debug('Parsing config page.', 'reddit')
                config = json.loads(page.content_md)
            except:
                logger.log_error('Failed to parse config page.', 'reddit')
                time.sleep(15)
                continue

            # Check if within window
            logger.log_debug('Checking window.', 'status')
            current_time = datetime.datetime.now()
            current_date = current_time.strftime('%d-%m-%Y')
            within_window = check_window(config.get('start_time', '02:00'),
                                         config.get('stop_time', '22:00'),
                                         current_time.strftime('%H:%M'))
            if not within_window:
                logger.log_debug('Not within window, waiting 5 minutes.', 'status')
                time.sleep(300)
                continue
            else:
                logger.log_debug('Within window, continuing.', 'status')

            # Check if thread already started
            logger.log_debug('Checking for current post.', 'status')
            if current_date == state.get('post_date', ''):
                post_id = state.get('post_id', None)
                logger.log_debug('Found post: %s' % post_id, 'status')
            else:
                post_id = None
                logger.log_debug('No post found.', 'status')

            # Create post if no post id
            if post_id:
                try:
                    logger.log_debug('Fetching post.', 'reddit')
                    post = reddit.get_submission(submission_id=post_id)
                except:
                    logger.log_error('Could not fetch post.', 'reddit')
                    time.sleep(15)
                    continue
            else:
                try:
                    logger.log_info('Creating post.', 'reddit')
                    title = current_time.strftime(config['post_title'])
                    body = config['post_text']
                    post = subreddit.submit(title, body)
                    state['removed_comments'] = []
                except:
                    logger.log_error('Could not create post.', 'reddit')
                    time.sleep(15)
                    continue

            # Dump state for crash safety
            state['post_id'] = post.id
            state['post_date'] = current_date
            if not state == old_state:
                try:
                    logger.log_debug('Writing state file.', 'io')
                    utils.write_json(state, 'state.json')
                    old_state = copy.deepcopy(state)
                except:
                    logger.log_error('Unable to write state file.', 'io')
                    time.sleep(15)
                    continue

            # Clean top level comments
            try:
                logger.log_debug('Loading approved commentors.', 'status')
                removed_comments = state.get('removed_comments', [])
                approved_commentors = config.get('approved_commentors', [])
                approved_commentors.append(settings['reddit']['username'])
                logger.log_debug('Cleaning comments.', 'reddit')
                for comment in post.comments:
                    logger.log_debug('Parsing comment tree: %s' % comment.permalink, 'reddit')
                    parse_comment_tree(comment, approved_commentors, removed_comments)
            except:
                logger.log_error('Unable to clean comments.', 'reddit')
                time.sleep(15)
                continue

            # Dump state for crash safety
            state['removed_comments'] = removed_comments
            if not state == old_state:
                try:
                    logger.log_debug('Writing state file.', 'io')
                    utils.write_json(state, 'state.json')
                    old_state = copy.deepcopy(state)
                except:
                    logger.log_error('Unable to write state file.', 'io')
                    time.sleep(15)
                    continue

            # Build list of new videos to post
            new_videos = []
            channel_states = state.get('channels', {})
            try:
                for channel in config.get('channels', []):
                    logger.log_debug('Fetching videos: %s' % channel, 'youtube')
                    channel_state = channel_states.get(channel, {'name': channel})
                    videos, channel_states[channel] = get_new_videos(channel_state,
                                                                     settings['youtube']['api_key'])
                    if len(videos) == 0:
                        logger.log_debug('No new videos.', 'youtube')
                    elif len(videos) >= 5:
                        logger.log_error('Too many videos: %s' % channel, 'youtube')
                    else:
                        logger.log_debug('Added videos: %s' % len(videos), 'youtube')
                        new_videos.extend(videos)
                        channel_states[channel]['after'] = videos[0]['date']
            except:
                logger.log_error('Error fetching new videos.', 'youtube')
                time.sleep(15)
                continue

            # Submit video comments
            for video in new_videos:
                try_counter = 0
                while True:
                    try_counter += 1
                    logger.log_debug('Processing Comment: %s' % video['id'], 'reddit')
                    text = config.get('comment_text', u'[{channel}] [{title}]({url})')
                    try:
                        logger.log_debug('Formatting Comment: %s' % video['id'], 'reddit')
                        text = text.format(channel=video['channel'],
                                           title=video['title'],
                                           id=video['id'],
                                           url=video['url'])
                        logger.log_info('Submitting Comment: %s' % video['id'], 'reddit')
                        post.add_comment(text)
                        break
                    except:
                        if try_counter >= 5:
                            logger.log_error('Skipping Comment: %s' % video['id'], 'reddit')
                            break
                        logger.log_error('Submit Failed: %s' % video['id'], 'reddit')
                        time.sleep(5)
                        continue

            # Dump state for crash safety
            state['channels'] = channel_states
            if not state == old_state:
                try:
                    logger.log_debug('Writing state file.', 'io')
                    utils.write_json(state, 'state.json')
                    old_state = copy.deepcopy(state)
                except:
                    logger.log_error('Unable to write state file.', 'io')
                    time.sleep(15)
                    continue

            # Wait before cycling again to be nice to the APIs
            time.sleep(5)

        except KeyboardInterrupt:
            logger.log_debug('Interrupt recieved.', 'status')
            break

def get_new_videos(state, api_key):
    if not state.has_key('id'):
        channel = get_channel(state['name'], api_key)
        state.update(channel)
    after = state.get('after', None)
    videos = get_videos(state, api_key, after)
    return videos, state

def get_channel(user, api_key):
    url = u'https://www.googleapis.com/youtube/v3/channels'
    params = {'key': api_key, 'part': 'snippet', 'forUsername': user}
    resp = requests.get(url, params=params)
    if not resp.ok:
        raise Exception('Unable to load channel id!')
    try:
        channel = resp.json()['items'][0]
    except:
        raise Exception('No channels found!')
    channel = {'title': channel['snippet']['title'],
               'id': channel['id']}
    return channel

def get_videos(channel, api_key, after=None, limit=10):
    url = u'https://www.googleapis.com/youtube/v3/search'
    params ={'key': api_key, 'part': 'snippet',
             'channelId': channel['id'], 'maxResults': limit,
             'type': 'video', 'order': 'date',
             'safeSearch': 'none'}
    if after:
        params['publishedAfter'] = after
    resp = requests.get(url, params=params)
    if not resp.ok:
        raise Exception('Unable to load videos!')
    base_url = u'https://www.youtube.com/watch?v={id}'
    videos = []
    for video in resp.json()['items']:
        if video['snippet']['publishedAt'] == after:
            continue
        videos.append({'id': video['id']['videoId'],
                       'title': video['snippet']['title'],
                       'url': base_url.format(id=video['id']['videoId']),
                       'channel': channel['title'],
                       'date': video['snippet']['publishedAt']})
    return videos

def parse_comment_tree(comment, approved_commentors, removed_comments, in_tree=False):
    if isinstance(comment, praw.objects.MoreComments):
        for sub_comment in comment.comments():
            parse_comment_tree(sub_comment, approved_commentors, removed_comments, in_tree)
    elif in_tree:
        for reply in comment.replies:
            parse_comment_tree(reply, approved_commentors, removed_comments, in_tree)
        if not comment.id in removed_comments:
            comment.remove()
            removed_comments.append(comment.id)
    elif not hasattr(comment.author, 'name'):
        for reply in comment.replies:
            parse_comment_tree(reply, approved_commentors, removed_comments, in_tree=True)
        if not comment.id in removed_comments:
            comment.remove()
            removed_comments.append(comment.id)
    elif not comment.author.name in approved_commentors:
        for reply in comment.replies:
            parse_comment_tree(reply, approved_commentors, removed_comments, in_tree=True)
        if not comment.id in removed_comments:
            comment.remove()
            removed_comments.append(comment.id)

def check_window(start_time, stop_time, current_time):
    current_time = map(int, current_time.split(':'))
    start_time = map(int, start_time.split(':'))
    stop_time = map(int, stop_time.split(':'))
    current_time = datetime.time(current_time[0], current_time[1], 0)
    start_time = datetime.time(start_time[0], start_time[1], 0)
    stop_time = datetime.time(stop_time[0], stop_time[1], 0)
    if start_time <= stop_time:
        return start_time <= current_time <= stop_time
    else:
        return start_time <= current_time or current_time <= stop_time

if __name__ == '__main__':
    main()

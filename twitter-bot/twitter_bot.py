# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 01:35:19 2013

@author: chipolux
"""
import praw
import tweepy

import json
import logging
import sys
from datetime import datetime


# Create logger
Logger = logging.getLogger('TwitterBotLogger')
Handler = logging.FileHandler('Twitter_Bot.log')
Formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
Handler.setFormatter(Formatter)
Logger.addHandler(Handler)
Logger.setLevel(logging.INFO)

# Define logging wrapper functions
def writeInfo(Message):
    Logger.info(' %s' % Message)
def writeError(Message):
    Logger.error(Message)
def writeDebug(Message):
    Logger.debug(Message)

# Begin
writeInfo('Beginning sequence.')

# Load text from file
try:
    with open('settings.json', 'r') as f:
        SettingsFile = f.read()
except IOError:
    #print 'No settings.json file.'
    writeError('No settings file.')
    sys.exit()

# Parse file text into object using JSON
try:
    Settings = json.loads(SettingsFile)
except:
    #print 'Invalid JSON in settings.json.'
    writeError('Unable to parse JSON in settings file.')
    sys.exit()

# Try and grab last tweet posted
try:
    with open('lasttweet', 'r') as f:
        LastTweet = f.readline()
        writeDebug('Last tweet posted: %s' % LastTweet)
except IOError:
    LastTweet = None
    writeDebug('No last tweet found, setting to None.')

# Initialize reddit
try:
    Reddit = praw.Reddit(user_agent=Settings['Reddit']['UserAgent'])
    Reddit.login(Settings['Reddit']['Username'], Settings['Reddit']['Password'])
    Subreddit = Reddit.get_subreddit(Settings['Reddit']['Subreddit'])
except:
    #print 'Unable to connect to reddit.'
    writeError('Unable to connect to reddit.')
    sys.exit()

# Initialize twitter
try:
    Auth = tweepy.OAuthHandler(Settings['Twitter']['ConsumerKey'],
                               Settings['Twitter']['ConsumerSecret'])
    Auth.set_access_token(Settings['Twitter']['AccessKey'],
                          Settings['Twitter']['AccessSecret'])
    Twitter = tweepy.API(Auth)
    Tweets = Twitter.user_timeline(Settings['Twitter']['Username'], since_id=LastTweet)
    Tweets.reverse()
except:
    #print 'Unable to connect to twitter.'
    writeError('Unable to connect to twitter.')
    sys.exit()

# Check if any new tweets
if len(Tweets) <= 0:
    #print 'No new tweets.'
    writeInfo('No new tweets to post. Exiting.')
    sys.exit()
#elif len(Tweets) < 5:
#    #print 'Not enough tweets to post.'
#    writeInfo('Not enough tweets to post. Exiting.')
#    sys.exit()

# Remove special reddit characters from user id
RedditSpecialChars = ['*', '^', '~', '[', ']', '(', ')', '_']
User = Settings['Twitter']['Username']
for Character in RedditSpecialChars:
    User = User.replace(Character, '')

# Define post template strings
PostTitle = u'%s Tweet Report - %s' % (Settings['Twitter']['Username'], datetime.utcnow().strftime('%d/%m/%Y'))
TextTitle = (u'**_{User} Tweets_** '
              '(Oldest On Top - Contact /u/{Owner} with any suggestions or questions!)\n\n'
              'Date|Text\n'
              ':|:\n')
TextPost = u'{Date}|[{Text}](http://twitter.com/{User}/status/{TweetID})\n'

# Build post from templates and tweets
Body = "%s" % TextTitle.format(User = User, Owner = Settings['Reddit']['BotOwner'])
Tweet = None
for Tweet in Tweets:
    writeInfo('Formatting tweet: %s' % Tweet.id_str)
    try:
        # Strip out anything above utf-8
        clean = ''.join(c for c in Tweet.text if ord(c) < 2047).strip()
        clean = clean.replace('\n', ' ')
        Entry = TextPost.format(Text = clean,
                                Date = Tweet.created_at,
                                User = Tweet.user.id_str,
                                TweetID = Tweet.id_str)
        writeDebug('Formatted tweet: %s' % Tweet.id_str)
        Body = Body + Entry
    except:
        writeError('Unable to format tweet: %s' % Tweet.id_str)

# Write last tweet id to file
try:
    if Tweet != None:
        writeDebug('Setting new last tweet: %s' % Tweet.id_str)
        with open('lasttweet', 'w') as f:
            f.write(Tweet.id_str)
except:
    #print 'Unable to write lasttweet.'
    writeError('Unable to log last tweet id.')
    sys.exit()

# Submit post to reddit
try:
    #print Body
    writeInfo('Submitting tweet post.')
    Subreddit.submit(PostTitle, Body)
except:
    #print 'Unable to submit post.'
    writeError('Unable to submit tweets to reddit.')
    sys.exit()

#print 'Completed Twitter Posts'
writeInfo('Tweet sequence complete.')

# -*- coding: utf-8 -*-
"""
Created on Thu Apr 18 01:20:23 2013

@author: chipolux
"""
import gdata.youtube.service
import json
import praw
import logging
import sys

# Create logger
Logger = logging.getLogger('YouTubeBotLogger')
Handler = logging.FileHandler('YouTube_Bot.log')
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

# Try and grab last video posted
try:
    with open('lastvideo', 'r') as f:
        LastVideo = f.readline()
        writeDebug('Last video posted: %s' % LastVideo)
except IOError:
    LastVideo = None
    writeDebug('No last video found, setting to None.')

# Initialize reddit
try:
    Reddit = praw.Reddit(user_agent=Settings['Reddit']['UserAgent'])
    Reddit.login(Settings['Reddit']['Username'], Settings['Reddit']['Password'])
    Subreddit = Reddit.get_subreddit(Settings['Reddit']['Subreddit'])
except:
    #print 'Unable to connect to reddit.'
    writeError('Unable to connect to reddit.')
    sys.exit()

# Initialize youtube grab channel object
try:
    YouTube = gdata.youtube.service.YouTubeService()
    Channel = YouTube.GetYouTubeUserFeed(username=Settings['YouTube']['Username'])
except:
    #print 'Unable to connect to youtube.'
    writeError('Unable to connect to youtube.')
    sys.exit()

# Parse out Title, Url, and Id from video entries
# Also checks each entry againts lastvideo so we only get new videos
Feed = Channel.entry
Videos = []
for Entry in Feed:
    Title = str(Entry.title.text)
    Id = str(Entry.id.text.split('/')[-1])
    Url = str(Entry.media.player.url)
    if LastVideo == Id:
        break
    else:
        Videos.append((Title, Id, Url))

# Check if any new videos
if len(Videos) <= 0:
    #print 'No new videos.'
    writeInfo('No new videos to post. Exiting.')
    sys.exit()
elif len(Videos) >= 7:
    #print 'More than 7 videos to post, manual intervention required.'
    writeError('Too many videos to post, please advise.')
    sys.exit()

# Grab recent posts to subreddit
RecentUrls = []
try:
    Recent = Subreddit.get_new()
    for Post in Recent:
        RecentUrls.append(str(Post.url))
except:
    #print 'Unable to retrieve recent reddit posts.'
    writeError('Unable to retrieve recent reddit posts.')
    sys.exit()

# Check if video already posted
# If not posted try to post
Videos.reverse()
for Video in Videos:
    for Url in RecentUrls:
        if Video[1] in Url:
            Video = None
            break
    if Video != None:
        #print 'Posting Video: %s' % Video[0]
        writeInfo('Posting Video: %s' % Video[0])
        try:
            Subreddit.submit(Video[0], url=Video[2])
        except:
            #print 'Unable To Post: %s' % Video[0]
            writeError('Unable To Post, Exiting: %s ' % Video[0])
            sys.exit()

# Write last video id to file
if Video == None:
    Video = Videos[-1]
try:
    writeDebug('Setting new last video: %s' % str(Video[1]))
    with open('lastvideo', 'w') as f:
        f.write(str(Video[1]))
except:
    #print 'Unable to write lastvideo.'
    writeError('Unable to log last video.')
    sys.exit()

#print 'Completed YouTube Posts'
writeInfo('YouTube sequence complete.')
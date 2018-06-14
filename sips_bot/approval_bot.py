# -*- coding: utf-8 -*-
"""
Created on Mon May 27 17:34:29 2013

@author: chipolux
"""
import json
import praw
import logging
import sys

# Create logger
Logger = logging.getLogger('ApprovaleBotLogger')
Handler = logging.FileHandler('Approval_Bot.log')
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

# Initialize reddit
try:
    Reddit = praw.Reddit(user_agent=Settings['Reddit']['UserAgent'])
    Reddit.login(Settings['Reddit']['Username'], Settings['Reddit']['Password'])
    Subreddit = Reddit.get_subreddit(Settings['Reddit']['Subreddit'])
except:
    #print 'Unable to connect to reddit.'
    writeError('Unable to connect to reddit.')
    sys.exit()

# Retrieve items needing moderation
try:
    SpamQueue = Subreddit.get_spam(limit=0)
    #ModQueue = Subreddit.get_mod_queue()
    #UnmoderatedQueue = Subreddit.get_unmoderated()
    #ReportQueue = Subreddit.get_reports()
except:
    writeError('Unable to retrieve post listings.')
    sys.exit()

# Parse and approve items in mod queue
approved_list = []
for item in SpamQueue:
    if item.banned_by == True:
        if type(item) == praw.objects.Submission:
            # Process submission
            approved_list.append('Approved Submission: %s' % item.permalink)
            writeInfo('Approved Submission: %s' % item.permalink)
            item.approve()
        elif type(item) == praw.objects.Comment:
            # Process comment
            approved_list.append('Approved Comment: %s' % item.permalink)
            writeInfo('Approved Comment: %s' % item.permalink)
            item.approve()
        else:
            writeError('Unknown item type: %s' % item.permalink)
            approved_list.append('Unknown Item Type: %s' % item.permalink)

# Set message template
subject_template = '{Bot} Approval Report'
head_template = 'Approved Items\n-\n---\n\n'
line_template = '{Text}\n\n---\n\n'

# Create and send message to bot owner
if len(approved_list) > 0:
    subject = subject_template.format(Bot=Settings['Reddit']['Username'])
    body = head_template
    for line in approved_list:
        body += line_template.format(Text=line)
    #Reddit.send_message(Settings['Reddit']['BotOwner'], subject, body)

#print 'Completed Auto Approvals'
writeInfo('Approvals sequence complete.')
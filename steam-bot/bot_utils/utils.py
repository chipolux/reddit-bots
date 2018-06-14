# -*- coding: utf-8 -*-
"""
Created on Sat Sep 07 19:13:01 2013

@author: chipolux
"""
import requests
import praw

from email.mime.text import MIMEText
import threading
import smtplib
import logging
import time
import json
import sys
import os

# Get current path
MAIN_DIR = os.path.split(os.path.abspath(__file__))[0]

# Custom generic thread class
class GenericThread(threading.Thread):
    def __init__(self, function, *args, **kwargs):
        threading.Thread.__init__(self)
        self.function = function
        self.args = args
        self.kwargs = kwargs
    def run(self):
        self.function(*self.args, **self.kwargs)
        return

# Class to wrap up simple logging
class Logger:
    """
    Wrap up basic logging for ease of use.
    
    Keyword Arguments:
    path     -- Name the file to write log entries to, automatically placed in current dir.
    handle   -- The unique handle for this instance of the logging subsystem.
    level    -- INFO, ERROR, or DEBUG to set what level to log.
    rotation -- Number of bytes to rotate log file on, doesn't rotate if 0.
    remote   -- If this logger should report to a remote API.
    url      -- URL of remote API for reporting.
    key      -- API key for remote API.
    """
    def __init__(self, path='default.log', handle="logger", level='info', rotation=0,
                 remote=False, url=None, key=None):
        """Initializes logger object and adds formatting."""
        if rotation > 0:
            backup_path = os.path.join(MAIN_DIR, 'old_logs')
            log_path = os.path.join(MAIN_DIR, path)
            if os.path.exists(log_path):
                current_size = os.path.getsize(log_path)
                if current_size >= rotation:
                    if not os.path.exists(backup_path):
                        os.mkdir(backup_path)
                    new_file = path.replace('.log', '_%d.log' % time.time())
                    os.rename(log_path, os.path.join(backup_path, new_file))
        self._logger = logging.getLogger(handle)
        handler = logging.FileHandler(path)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
        try:
            self._logger.setLevel(logging.__dict__[level.upper()])
        except:
            self._logger.setLevel(logging.DEBUG)
        self.errors = []
        self.name = handle
        self.remote = remote
        self.remote_url = url
        self.remote_key = key
    
    def __del__(self):
        for handler in self._logger.handlers:
            self._logger.removeHandler(handler)
    
    def log_info(self, message, category='none'):
        """Wraps info function to standardize output."""
        log = {'source': self.name, 'created': time.time(), 'level': 'info',
               'category': category, 'message': message, 'key': self.remote_key}
        message = [log['created'], log['level'], log['category'], log['message']]
        self._logger.info(json.dumps(message))
        if self.remote:
            resp = requests.post(self.remote_url, params=log)
            message[1] = 'error'
            message[2] = 'remote_logging'
            if resp.ok:
                data = resp.json()
                if data['status'] != 'ok':
                    message[3] = 'Log Not Accepted: %s' % log['message']
                    self._logger.error(json.dumps(message))
            else:
                message[3] = 'Unable To Send: %s' % log['message']
                self._logger.error(json.dumps(message))
    
    def log_error(self, message, category='none'):
        """Wraps error function to standardize output."""
        log = {'source': self.name, 'created': time.time(), 'level': 'error',
               'category': category, 'message': message, 'key': self.remote_key}
        message = [log['created'], log['level'], log['category'], log['message']]
        self._logger.error(json.dumps(message))
        self.errors.append(json.dumps(message))
        if self.remote:
            resp = requests.post(self.remote_url, params=log)
            message[1] = 'error'
            message[2] = 'remote_logging'
            if resp.ok:
                data = resp.json()
                if data['status'] != 'ok':
                    message[3] = 'Log Not Accepted: %s' % log['message']
                    self._logger.error(json.dumps(message))
            else:
                message[3] = 'Unable To Send: %s' % log['message']  
                self._logger.error(json.dumps(message))
    
    def log_debug(self, message, category='none'):
        """Wraps debug function to standardize output."""
        log = {'source': self.name, 'created': time.time(), 'level': 'debug',
               'category': category, 'message': message, 'key': self.remote_key}
        message = [log['created'], log['level'], log['category'], log['message']]
        self._logger.debug(json.dumps(message))
        if self.remote:
            resp = requests.post(self.remote_url, params=log)
            message[1] = 'error'
            message[2] = 'remote_logging'
            if resp.ok:
                data = resp.json()
                if data['status'] != 'ok':
                    message[3] = 'Log Not Accepted: %s' % log['message']
                    self._logger.error(json.dumps(message))
            else:
                message[3] = 'Unable To Send: %s' % log['message']
                self._logger.error(json.dumps(message))

# Function to pass errors on to bot owner and close
def safe_exit(logger, email=False, email_to=None, email_from=None,
              email_server=None, email_port=25, email_user=None,
              email_pass=None):
    if len(logger.errors) > 0:
        email_message = 'Bot Error Report:\n\n'
        for error in logger.errors:
            email_message += 'ERROR: %s\n' % error
        if email:
            try:
                email_message = MIMEText(email_message)
                email_message['Subject'] = '%s Error Report' % logger.name
                email_message['From'] = email_from
                email_message['To'] = ', '.join(email_to)
                email_server = smtplib.SMTP(email_server, email_port)
                email_server.starttls()
                email_server.login(email_user, email_pass)
                email_server.sendmail(email_message['From'],
                                      email_message['To'],
                                      email_message.as_string())
                email_server.quit()
            except:
                logger.log_error('Unable to send error report via email.', 'safe_exit')
        else:
            logger.log_debug('Email error reporting disabled.', 'safe_exit')
    sys.exit()

if __name__ == '__main__':
    # Test logger class
    logger = Logger(level='debug')
    logger.log_debug('Test debug Message')
    logger.log_info('Test info Message')
    logger.log_error('Test error Message')
    logger.log_info({'action': 'Test of dict logs.', 'msg': 'Just a test.'})
    logger.log_info('Log Should Now Rotate')
    del(logger)
    logger = Logger(rotation=1)
    logger.log_info('Test of categories.', 'misc')
    logger.log_debug({'action': 'This wont show up.', 'msg': 'Test.'}, 'dict_log')
    logger.log_info({'action': 'This should.', 'msg': 'Test.'}, 'dict_log')
    del(logger)
    logger = Logger(handle='test', remote=True, url='http://api.nbwright.net/logging', key='fake_key')
    logger.log_info('Info Test', 'testing')
    logger.log_debug('Debug Test', 'testing')
    logger.log_error('Error Test', 'testing')

#!/usr/bin/env python3.8

'Logging.'

import sys
from farmware_tools import device


class Log():
    'Log messages.'

    def __init__(self, settings):
        self.settings = settings
        self.sent = []

    def log(self, message, type_=None, channels=None):
        'Log a message.'
        if self.settings['verbose'] > 0:
            device.log(message, type_, channels)
            self.sent.append({
                'message': message,
                'type': type_,
                'channels': channels,
            })

    def debug(self, message):
        'Send error message.'
        if self.settings['verbose'] > 2:
            self.log(message, 'debug')

    def error(self, message):
        'Send error message.'
        self.log(message, 'error')
        if self.settings['exit_on_error']:
            sys.exit(1)

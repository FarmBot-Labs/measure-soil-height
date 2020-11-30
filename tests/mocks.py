#!/usr/bin/env python3.8

'Mocks.'

from copy import copy
import numpy as np


class MockDevice():
    'Mock device.'

    def __init__(self):
        self.position_history = [{'x': 0, 'y': 0, 'z': 0}]
        self.log_history = []
        self.pin_history = []

    def log(self, message, **_kwargs):
        'Log a message.'
        self.log_history.append(message)

    def get_current_position(self):
        'Get current device coordinates.'
        return copy(self.position_history[-1])

    def move_relative(self, **kwargs):
        'Relative movement.'
        position = self.get_current_position()
        position['x'] += kwargs['x']
        position['y'] += kwargs['y']
        position['z'] += kwargs['z']
        self.position_history.append(position)

    def write_pin(self, **kwargs):
        'Write pin value.'
        self.pin_history.append(kwargs)


class MockCV():
    'Mock OpenCV.'

    def __init__(self):
        self.CAP_PROP_FRAME_WIDTH = 'width'
        self.CAP_PROP_FRAME_HEIGHT = 'height'
        self.capture_count = 0
        self.parameter_history = {}

        class MockVideoCapture():
            'Mock VideoCapture.'

            def __init__(self, port):
                self.port = port

            @staticmethod
            def grab():
                'Get frame.'
                self.capture_count += 1
                return True

            @staticmethod
            def read():
                'Get image.'
                self.capture_count += 1
                img = np.zeros([100, 100, 3], np.uint8)
                col = 40 if self.capture_count % 2 == 0 else 50
                img[:, col:(col + 10)] = 255
                return True, img

            @staticmethod
            def set(key, value):
                'Set parameter.'
                self.parameter_history[key] = value

        self.VideoCapture = MockVideoCapture

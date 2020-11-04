#!/usr/bin/env python3.8

'Generate simple plot.'

import numpy as np
import cv2 as cv
from histogram import FONT, WHITE


class Plot():
    'Generate simple plot.'

    def __init__(self, results):
        self.plot = np.zeros((1000, 1000), dtype=np.uint8)
        self.height, self.width = self.plot.shape[:2]
        self.results = results
        self.intercept = 0
        self.slope = 0
        self.y_values = None

    def _position_from_percent(self, percent_x, percent_y):
        return (int(self.height * percent_y / 100.),
                int(self.width * percent_x / 100.))

    def add_text(self, text, percent_x, percent_y):
        'Add text to plot.'
        position = self._position_from_percent(percent_x, percent_y)
        self.plot = cv.putText(self.plot, text, position, FONT, 1, WHITE, 1)

    def add_labels(self):
        'Add labels to plot.'
        # Origin
        self.add_text('0', 99, 1)

        # X axis
        self.add_text('disparity', 99, 50)
        self.add_text('1000', 99, 95)
        x_intercept = -int(self.intercept / self.slope)
        self.add_text(str(x_intercept), 99, x_intercept / self.width * 100)

        # Y axis
        self.add_text('distance', 50, 1)
        self.add_text('1000', 3, 1)
        for y_value in self.y_values:
            self.add_text(str(y_value), self.height - int(y_value), 50)

        # Legend
        self.add_text('calculated', 10, 90)
        calculated = self._position_from_percent(10, 88)
        self.plot = cv.circle(self.plot, calculated, 10, WHITE, 1)
        self.add_text('expected', 15, 90)
        expected = self._position_from_percent(15, 88)
        self.plot = cv.circle(self.plot, expected, 5, WHITE, 2)

    def line(self, slope, intercept, thickness=1):
        'Add line to plot.'
        self.intercept = intercept
        self.slope = slope
        start = (0, int(intercept))
        end = (self.width, int(self.width * slope + intercept))
        self.plot = cv.line(self.plot, start, end, WHITE, thickness)

    def points(self, x_values, y_values, size=5, thickness=1):
        'Add points to plot.'
        self.y_values = y_values
        for x_value, y_value in zip(x_values, y_values):
            point = (int(x_value), int(y_value))
            self.plot = cv.circle(self.plot, point, size, WHITE, thickness)

    def save(self, filename):
        'Save plot to file.'
        self.plot = np.flipud(self.plot).astype(np.uint8)
        self.add_labels()
        self.results.save_image(filename, self.plot)

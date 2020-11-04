#!/usr/bin/env python3.8

'Generate histogram.'

from statistics import NormalDist
import numpy as np
import cv2 as cv

GRAY = [200] * 3
RED = (100, 100, 255)
GREEN = (100, 255, 100)
PURPLE = (155, 100, 100)
LIGHT_RED = (100, 100, 150)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
FONT = cv.FONT_HERSHEY_PLAIN


def normalize(data, range_max, new_width, range_min=0):
    'Normalize data to new width.'
    data_width = (range_max - range_min) or 1
    return ((data - range_min) / data_width * new_width).astype(int)


class Histogram():
    'Generate histogram.'

    def __init__(self, image_data, calc_soil_z, simple=False):
        self.simple = simple
        self.calc_soil_z = calc_soil_z
        data = image_data.data
        self.reduced = image_data.reduced
        self.data = {
            'data': data,
            'mid': data[self.reduced['masks']['mid']],
        }
        try:
            prev_mid = data[self.reduced['history'][-2]['masks']['mid']]
        except IndexError:
            prev_mid = self.data['mid']
        self.data['prev_mid'] = prev_mid
        self.stats = self.reduced['stats']
        self.params = {
            'min': data.min() - (2 if simple else 100),
            'max': data.max() + (2 if simple else 100),
            'bin_count': 256 if simple else 200,
            'height': 1000,
        }
        self.params['width'] = self.params['bin_count'] * 12
        size = (self.params['height'], self.params['width'], 3)
        background_color = BLACK
        self.histogram = np.full(size, background_color, np.uint8)
        self.generate()

    def bin_color(self, i, bins, counts, color):
        'Get bin color.'
        if self.simple:
            return [200] * 3
        x_position = i / float(len(counts))
        gray = [int(x_position * 255)] * 3
        mid = self.data['mid']
        prev_mid = self.data['prev_mid']
        if len(mid) < 1:
            return gray
        if prev_mid.min() < bins[i] < prev_mid.max():
            if mid.min() < bins[i] < mid.max():
                return GREEN
            return gray
        if color is not None:
            return LIGHT_RED if bins[i] < mid.min() else RED
        return gray

    def plot_bins(self, counts, bins, max_value, color=None, fill=True):
        'Plot bin counts on histogram.'
        width, height = self.params['width'], self.params['height']
        normalized_counts = normalize(counts, max_value, height)
        for i, count in enumerate(normalized_counts):
            bin_width = int(width / (bins.size - 1))
            y_top = height - count
            y_bottom = height if fill else y_top + 2
            x_left = bin_width * i
            x_right = bin_width * (i + 1) - 0
            bin_color = self.bin_color(i, bins, counts, color)
            self.histogram[y_top:y_bottom, x_left:x_right] = bin_color

    def plot_text(self, text, location, thickness=2):
        'Add text to histogram.'
        self.histogram = cv.putText(
            self.histogram, text, location, FONT, 1.5, WHITE, thickness)

    def plot_value(self, line):
        'Plot vertical line and label at value on histogram.'
        value_x = line['value']
        params = self.params
        hist_x = normalize(
            value_x, params['max'], params['width'], params['min'])
        self.histogram[:, hist_x:(hist_x + 2)] = line['color']
        soil_z, _ = self.calc_soil_z(value_x)
        within_range = self.stats['threshold'] < value_x < self.stats['max']
        plot_z = not self.simple and within_range and soil_z is not None
        soil_z_str = f' (z={soil_z})' if plot_z else ''
        label = f'{value_x:.0f}{soil_z_str}'
        align_left = value_x < self.stats['mid']
        label_x = (hist_x - len(label) * 15) if align_left else hist_x
        location = (max(0, label_x), line['y_label'])
        self.plot_text(label, location)

    def plot_lines(self):
        'Plot lines and labels at values of interest.'
        lines = [
            {'value': 0, 'color': GRAY, 'y_label': 180},
            {'value': self.stats['threshold'], 'color': GRAY, 'y_label': 150},
            {'value': self.stats['low'], 'color': RED, 'y_label': 120},
            {'value': self.stats['mid'], 'color': GREEN, 'y_label': 80},
            {'value': self.stats['high'], 'color': RED, 'y_label': 120},
            {'value': self.stats['max'], 'color': GRAY, 'y_label': 180},
        ]
        if self.simple:
            lines = [{'value': self.stats['threshold'],
                      'color': GRAY, 'y_label': 150}]
        for line in lines:
            self.plot_value(line)

    def calculate_bins(self, data):
        'Generate histogram data.'
        x_range = (self.params['min'], self.params['max'])
        return np.histogram(data, self.params['bin_count'], x_range)

    def generate(self):
        'Make histogram.'
        if self.simple:
            counts, bins = self.calculate_bins(self.data['data'])
            self.generate_text_histogram(counts, bins)
            self.plot_bins(counts, bins, counts.max())
            self.plot_lines()
            return
        counts, bins = self.calculate_bins(self.data['mid'])
        all_counts, all_bins = self.calculate_bins(self.data['data'])
        self.generate_text_histogram(all_counts, all_bins)
        self.plot_bins(all_counts, bins, counts.max(), LIGHT_RED)
        self.plot_bins(counts, bins, counts.max())
        params = self.params
        bins = np.linspace(params['min'], params['max'], params['width'])
        norm = NormalDist(mu=self.stats['mu'], sigma=self.stats['sigma'])
        counts = np.array([norm.pdf(b) for b in bins])
        self.plot_bins(counts, bins, counts.max(), fill=False)
        self.plot_lines()
        self.plot_text('disparity', (int(params['width'] / 2), 20), 1)

    def generate_text_histogram(self, counts, bins):
        'Generate histogram text data.'
        hist_data = []
        normalized_counts = normalize(counts, counts.max(), 100)
        for bin_val, count, normalized in zip(bins, counts, normalized_counts):
            bin_end = bin_val + bins[1] - bins[0]
            bin_str = f'{count / self.data["data"].size * 100:>5.1f}% '

            def _bin_label(label, value):
                return f' {label}={value}' if bin_val <= value <= bin_end else ''
            bin_str += '=' * normalized
            for key in ['threshold', 'low', 'mid', 'high', 'max']:
                bin_str += _bin_label(key, self.stats[key])
            for i, record in enumerate(self.reduced['history'][::-1]):
                if i == 0:
                    continue
                for key in ['low', 'mid', 'high']:
                    bin_str += _bin_label(f'{key}_{i}', record['stats'][key])
            hist_data.append(f'{bin_val:6.1f} {bin_end:6.1f}: {bin_str}')
        self.reduced['histogram'] = hist_data

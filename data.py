#!/usr/bin/env python3

'Data for MeasureSoilHeight.'

import json
from copy import deepcopy
import numpy as np


class Data():
    'Reduce data.'

    def __init__(self, data, tag, settings):
        self.data = data
        self.tag = tag
        self.settings = settings
        self.reduced = {'masks': {}, 'stats': {}, 'history': []}
        self.report = None
        self.reduce_data()
        self.data_content_report()

    def _add_calculated(self, mean, sigma):
        masks = self.reduced['masks']
        masks['low'] = self.data < mean - sigma
        masks['high'] = self.data > mean + sigma
        mid = np.invert(masks['low']) * np.invert(masks['high'])
        masks['mid'] = masks['threshold'] * mid
        stats = self.reduced['stats']
        threshold = self.settings['pixel_value_threshold']
        stats['mu'] = max(threshold + 1, mean)
        stats['sigma'] = sigma
        stats['low'] = stats['mu'] - sigma
        stats['low_size_p'] = self._percent(self.data, masks['threshold'])
        stats['mid'] = stats['mu']
        stats['mid_size_p'] = self._percent(self.data, masks['mid'])
        stats['high'] = stats['mu'] + sigma
        stats['high_size_p'] = self._percent(self.data, masks['high'])

        record = deepcopy(self.reduced)
        record.pop('history')
        self.reduced['history'].append(record)

    def _find_highest_bin(self, mean, sigma):
        counts, bins = np.histogram(self.data, bins=200)
        bins = bins[:-1]
        mid_mask = (bins > mean - sigma) * (bins < mean + sigma)
        mid_bins = bins[mid_mask]
        mid_counts = counts[mid_mask]
        sorted_indexes = np.argsort(mid_counts)[::-1]
        first, second = sorted_indexes[:2]
        top = [
            {'bin': mid_bins[first], 'count': mid_counts[first]},
            {'bin': mid_bins[second], 'count': mid_counts[second]},
        ]
        mean = round(top[0]['bin'], 4)
        sigma = round(bins[1] - bins[0], 4)
        return mean, sigma, top

    def _mask_stats(self, mask):
        mean = round(self.data[mask].mean(), 4)
        sigma = round(self.data[mask].std(), 4)
        return mean, sigma

    def reduce_data(self):
        'Calculate masks and stats for data.'
        threshold = self.settings['pixel_value_threshold']
        masks = self.reduced['masks']
        masks['threshold'] = self.data > threshold
        stats = self.reduced['stats']
        stats['threshold'] = threshold
        stats['thresh_size_p'] = self._percent(self.data, masks['threshold'])
        stats['max'] = int(self.data.max())

        mean, sigma = self._mask_stats(self.data > threshold)
        self._add_calculated(mean, sigma)

        if self.tag != 'disparity':
            return

        new_mean, new_sigma, top = self._find_highest_bin(mean, sigma)
        if top[0]['bin'] > threshold and top[0]['count'] > 2 * top[1]['count']:
            if self.settings['verbose'] > 2:
                print('narrowing range: prominent bin count', top)
            mean, sigma = new_mean, new_sigma
            self._add_calculated(mean, sigma)

        if sigma > self.settings['wide_sigma_threshold']:
            if self.settings['verbose'] > 2:
                print('narrowing range: wide deviation')
            mean, sigma = self._mask_stats(self.reduced['masks']['mid'])
            self._add_calculated(mean, sigma)
            mean, sigma, top = self._find_highest_bin(mean, sigma)
            self._add_calculated(mean, sigma)

    @staticmethod
    def _percent(data, mask):
        return round(data[mask].size / float(data.size) * 100, 2)

    def data_content_report(self):
        'Return report, percent pixels above threshold, and average pixel value.'
        stats = self.reduced['stats']
        report = f'{self.tag}: '
        report += f'{stats["thresh_size_p"]}% > {stats["threshold"]}, '
        report += f'average value: {stats["mid"]:.0f}, '
        report += f'{stats["low"]:.0f} < {stats["mid_size_p"]}% < {stats["high"]:.0f}'
        self.report = {
            'report': report,
            'coverage': stats['thresh_size_p'],
            'mid': stats['mid'],
        }
        if self.settings['verbose'] > 2:
            counts = np.bincount(self.data.flatten() + 16)
            top_5 = np.argsort(counts)[::-1][:5]
            top_values = {'name': self.tag, 'top_values': {}}
            for pixel_value in top_5:
                val_percent = f'{counts[pixel_value] / self.data.size * 100:.1f}%'
                top_values['top_values'][int(pixel_value)] = val_percent
            print(json.dumps(top_values, indent=2))
            self.report['top_values'] = top_values
            self.report['report'] += f' top values: {top_values["top_values"]}'

#!/usr/bin/env python3.8

'Perform calculations on multiple stereo image sets.'

import os
import json
from calculate import Calculate
from plot import Plot


def _abridged(histogram):
    if len(histogram) < 1:
        return []
    low = ['low' in h for h in histogram].index(True)
    high = -['high' in h for h in histogram][::-1].index(True)
    return histogram[low:high]


class CalculateMultiple():
    'Calculate results for all stereo image sets.'

    def __init__(self, settings, log, image_sets=None):
        self.settings = settings
        self.log = log
        self.image_sets = image_sets
        self.set_results = []

    def calculate_multiple(self):
        'Run calculations for each image set.'
        if self.image_sets is None:
            self.log.error('No images provided.')
        for image_set in self.image_sets:
            calculation = Calculate(self.settings, self.log, image_set)
            details = calculation.calculate()
            if details is not None:
                disparity = calculation.output_images['disparity'].data.reduced
                histogram_data = disparity.get('histogram', [])
                details['histogram'] = _abridged(histogram_data)
                self.set_results.append(details)

        if len(self.image_sets) > 1 and self.settings['verbose'] > 1:
            self.plot(calculation.results)

        self.save_report()

    def plot(self, results):
        'Plot all set values.'
        if len(self.set_results) > 0:
            values = self.set_results[-1]['values']
            measured_distance = values['measured_distance']
            disparity_offset = values['disparity_offset']
            factor = values['calibration_factor']

            plot = Plot(results)
            plot.line(-factor, measured_distance + disparity_offset * factor)
            disparity = [r['values']['disparity'] for r in self.set_results]
            distance = [r['values']['calc_distance'] for r in self.set_results]
            expected = [r['values']['new_meas_dist'] for r in self.set_results]
            plot.points(disparity, distance, size=10)
            plot.points(disparity, expected, thickness=2)
            plot.save('plot')

    def save_report(self):
        'Save reduced data to file.'
        directory = self.settings['images_dir']
        if self.settings['verbose'] > 4 and directory == 'results':
            if not os.path.exists(directory):
                os.mkdir(directory)
            with open(f'{directory}/results.json', 'w') as results_file:
                results_file.write(json.dumps(self.set_results, indent=2))

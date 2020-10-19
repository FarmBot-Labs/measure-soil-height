#!/usr/bin/env python3

'Results output for MeasureSoilHeight.'

import os
import json
import cv2 as cv
from farmware_tools import app, set_config_value
from log import Log


class Results():
    'Save results.'

    def __init__(self, settings):
        self.settings = settings
        self.log = Log(settings)
        self.saved = {
            'farmware_env': [], 'points': [], 'images': [], 'data': [],
        }

    def set_calibration_factor(self, factor, height, width):
        'Save calculated calibration factor.'
        farmware_name = self.settings['farmware_name']
        configs = {
            'calibration_factor': factor,
            'calibration_image_width': width,
            'calibration_image_height': height,
        }
        farmware_name_lower = farmware_name.lower().replace(' ', '_')
        for key, value in configs.items():
            set_config_value(farmware_name, key, value)
            self.saved['farmware_env'].append({
                'key': f'{farmware_name_lower}_{key}',
                'value': value,
            })
        self.settings['calibration_factor'] = factor

    def save_soil_height(self, soil_z):
        'Save soil height.'
        if self.settings['edit_fbos_config']:
            app.patch('fbos_config', payload={'soil_height': soil_z})
        soil_height_point = {
            'pointer_type': 'GenericPointer',
            'name': 'Soil Height',
            'x': self.settings['initial_position'].get('x'),
            'y': self.settings['initial_position'].get('y'),
            'z': soil_z,
            'radius': self.settings['soil_height_point_radius'],
            'meta': {
                'created_by': 'measure-soil-height',
                'color': 'gray',
            },
        }
        app.post('points', soil_height_point)
        self.saved['points'].append(soil_height_point)
        self.log.log(f'Soil height saved: {soil_z}', 'success', ['toast'])

    def save_image(self, filename, image):
        'Save image.'
        images_dir = self.settings['images_dir']
        if not os.path.exists(images_dir):
            os.mkdir(images_dir)
        filepath = f'{images_dir}/{filename}.jpg'
        cv.imwrite(filepath, image)
        self.saved['images'].append(filepath)

    def save_report(self, name, output_data, input_data):
        'Save reduced data to file.'
        directory = self.settings['images_dir']
        if self.settings['verbose'] > 3 and directory == 'results':
            inputs = [i['reduced'] for d in input_data.values() for i in d]
            outputs = [output_data['disparity']]
            images = []
            for data in inputs + outputs:
                reduced = data.reduced
                images.append({
                    'name': data.tag,
                    'top_values': data.report['top_values']['top_values'],
                    'stats': reduced['stats'],
                    'stat_history': [d['stats'] for d in reduced['history'][:-1]],
                })
            filepath = f'{directory}/{name}_results.json'
            self.saved['data'].append(filepath)
            self.saved['data'].append(f'{directory}/settings.json')
            report = {
                'output': self.saved,
                'images': images,
            }
            if not os.path.exists(directory):
                os.mkdir(directory)
            with open(filepath, 'w') as results_file:
                results_file.write(json.dumps(report, indent=2))

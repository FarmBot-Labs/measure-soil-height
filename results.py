#!/usr/bin/env python3.8

'Results output.'

import os
import json
import cv2 as cv
from farmware_tools import app, set_config_value


class Results():
    'Save results.'

    def __init__(self, settings, log):
        self.settings = settings
        self.log = log
        self.saved = {
            'farmware_env': [], 'points': [], 'images': [], 'data': [],
            'logs': self.log.sent, 'fbos_config': [],
        }

    def save_calibration(self):
        'Save calculated calibration results.'
        farmware_name = self.settings['farmware_name']
        configs = {}
        for key in [k for k in self.settings if k.startswith('calibration_')]:
            configs[key] = self.settings[key]
        farmware_name_lower = farmware_name.lower().replace(' ', '_')
        for key, value in configs.items():
            set_config_value(farmware_name, key, value)
            self.saved['farmware_env'].append({
                'key': f'{farmware_name_lower}_{key}',
                'value': value,
            })

    def save_soil_height(self, soil_z):
        'Save soil height.'
        if self.settings['edit_fbos_config']:
            fbos_config_update = {'soil_height': soil_z}
            app.patch('fbos_config', payload=fbos_config_update)
            self.saved['fbos_config'].append(fbos_config_update)
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
        filesize = f'{os.path.getsize(filepath) / 1024.:.1f} KiB'
        self.saved['images'].append({'path': filepath, 'size': filesize})

    def save_report(self, name, output_data, input_data, calcs):
        'Save reduced data to file.'
        directory = self.settings['images_dir']
        if self.settings['verbose'] > 4 and directory == 'results':
            inputs = [i.data for d in input_data.values() for i in d]
            outputs = [output_data['disparity'].data]
            images = []
            for data in inputs + outputs:
                reduced = data.reduced
                images.append({
                    'name': data.info.get('name'),
                    'tag': data.info.get('tag'),
                    'coordinates': data.info.get('location'),
                    'calculations': calcs,
                    'top_values': data.report['top_values']['top_values'],
                    'histogram': reduced.get('histogram'),
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

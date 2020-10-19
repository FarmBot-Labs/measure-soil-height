#!/usr/bin/env python3

'Settings initialization for MeasureSoilHeight.'

import os
import json
from farmware_tools import device, get_config_value, env

DEFAULTS = {
    'input_coverage_threshold': 5,
    'disparity_coverage_threshold': 2,
    'pixel_value_threshold': 1,
    'repeat_capture_delay_s': 3,
    'image_offset_mm': 5,
    'blur': 0,
    'soil_height_point_radius': 0,
    'edit_fbos_config': False,
    'capture_count_at_each_location': 1,
    'image_blend_percent': 50,
    'wide_sigma_threshold': 10,
}

with open('manifest.json', 'r') as manifest_file:
    manifest_configs_list = json.load(manifest_file).get('config', {}).values()
manifest_configs = {config['name']: config for config in manifest_configs_list}


class Settings():
    'Farmware settings.'

    def __init__(self):
        self.farmware_name = 'Measure Soil Height'
        self.settings = {}
        self._init()
        self.save(self.settings['images_dir'])

    def _get_unlisted_config(self, key, default, type_=int):
        prefix = self.farmware_name.lower().replace(' ', '_')
        return type_(os.getenv(f'{prefix}_{key}', default))

    def _get_config(self, key):
        'Get config input.'
        try:
            return get_config_value(self.farmware_name, key, float)
        except KeyError:
            return manifest_configs[key]['value']

    def _init(self):
        'Load settings from env and state.'
        for key, default in DEFAULTS.items():
            self.settings[key] = self._get_unlisted_config(key, default)

        self.settings['farmware_name'] = self.farmware_name

        for key in manifest_configs.keys():
            self.settings[key] = self._get_config(key)

        width_key = 'take_photo_width'
        height_key = 'take_photo_height'
        self.settings['capture_width'] = float(os.getenv(width_key, '640'))
        self.settings['capture_height'] = float(os.getenv(height_key, '480'))

        rotation_key = 'CAMERA_CALIBRATION_total_rotation_angle'
        rotation_angle = float(os.getenv(rotation_key, '0'))
        self.settings['rotation'] = rotation_angle

        firmware_params = device.get_bot_state().get('mcu_params', {})
        self.settings['negative_z'] = firmware_params.get(
            'movement_home_up_z', 1)

        self.settings['initial_position'] = device.get_current_position() or {}
        self.settings['images_dir'] = env.Env().images_dir or 'results'

    def update(self, key, value):
        'Update a setting value.'
        self.settings[key] = value
        self.save(self.settings['images_dir'])

    def load(self, directory):
        'Load settings from file.'
        with open(f'{directory}/settings.json', 'r') as settings_file:
            self.settings = json.loads(settings_file)

    def save(self, directory):
        'Save settings to file.'
        settings = self.settings
        if settings['verbose'] > 3 and settings['images_dir'] == 'results':
            name = self.settings.get('image_base_name')
            name = name + '_' if name is not None else ''
            if not os.path.exists(directory):
                os.mkdir(directory)
            with open(f'{directory}/{name}settings.json', 'w') as settings_file:
                settings_file.write(json.dumps(settings, indent=2))

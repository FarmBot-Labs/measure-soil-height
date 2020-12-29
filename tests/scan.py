#!/usr/bin/env python3.8

'''Perform a full garden scan.

Steps (interactive):
 * Login to account
 * Set photo grid step size
 * Capture grid photos via an optimal path
 * Generate input files from captured images
 * Run Measure Soil Height for each input set
 * (optional) View results in 3D
 * (optional) Upload soil points to account
'''

import os
import sys
from time import sleep
from tests.account import get_token, get_input_value
from tests.account import generate_inputs, upload_points, CALIBRATION_KEYS
get_token()
if os.getenv('API_TOKEN') is not None:
    import farmware_tools as farmbot
    import numpy as np
    from tests.runner import TestRunner


def scan():
    'Take stereo photos of the entire garden bed.'
    print('Photo grid:')
    step_size = int(get_input_value('step size'))
    firmware_config = farmbot.app.get('firmware_config')
    web_app_config = farmbot.app.get('web_app_config')
    default_length = {'x': web_app_config.get('map_size_x', 2900),
                      'y': web_app_config.get('map_size_y', 1400), 'z': 400}
    axis_length = {}
    for axis in ['x', 'y', 'z']:
        steps = firmware_config.get(f'movement_axis_nr_steps_{axis}', 0)
        spm = firmware_config.get(f'movement_step_per_mm_{axis}', 1)
        axis_length[axis] = (steps / spm) or default_length[axis]
    print(f'axis lengths (mm): {axis_length}')
    proceed = input('Use full axis lengths? (Y/n) ') or 'y'
    if 'y' not in proceed.lower():
        axis_length['x'] = int(get_input_value('x limit'))
        axis_length['y'] = int(get_input_value('y limit'))
    x, y = np.mgrid[0:axis_length['x']:step_size, 0:axis_length['y']:step_size]
    grid_locations = None
    for i, stack in enumerate(np.dstack((x, y))):
        row = stack if i % 2 == 0 else stack[::-1]
        if grid_locations is None:
            grid_locations = row
        else:
            grid_locations = np.vstack((grid_locations, row))
    print(f'photo grid locations:\n{grid_locations}')
    proceed = input('Proceed to each location? (Y/n) ') or 'y'
    if 'y' in proceed.lower():
        for grid_x, grid_y in grid_locations:
            coordinate = farmbot.device.assemble_coordinate(
                int(grid_x), int(grid_y), 0)
            zero = farmbot.device.assemble_coordinate(0, 0, 0)
            farmbot.device.move_absolute(coordinate, 100, zero)
            sleep(1)
            farmbot.device.take_photo()
            farmbot.device.move_relative(0, 10, 0, 100)
            sleep(1)
            farmbot.device.take_photo()
            sleep(2)
        return_home = input('Return to home? (Y/n) ') or 'y'
        if 'y' in return_home.lower():
            farmbot.device.move_absolute(zero, 100, zero)


if __name__ == '__main__':
    prev_images = farmbot.app.get('images')
    prev_id = max([img['id'] for img in prev_images])
    scan()
    print('generating input data files...')
    farmware_envs = {env['key']: env['value']
                     for env in farmbot.app.get('farmware_envs')}
    parameters = {}
    for key in CALIBRATION_KEYS:
        parameters[key] = farmware_envs.get(f'measure_soil_height_{key}')
    if not all([v is not None for v in parameters.values()]):
        print('Calibration required.')
        sys.exit(1)
    filepath = generate_inputs(prev_id, prev_id, parameters)
    filename = filepath.split('/')[-1]
    output_filename = f'output_{filename}'
    runner = TestRunner()
    runner.verbosity = 5
    runner.include = [filename]
    runner.test_data_sets()
    response = input('View in 3D? (Y/n) ') or 'y'
    if 'y' in response.lower():
        from tests.view import IMPORT_LOAD_TIME, View
        view = View(IMPORT_LOAD_TIME, [output_filename])
        view.run()
    response = input('Upload points to account? (Y/n) ') or 'y'
    if 'y' in response.lower():
        upload_points(filename)

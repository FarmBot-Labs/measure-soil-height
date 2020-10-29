#!/usr/bin/env python3.8

'Run tests.'

import os
import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
from measure_height import MeasureSoilHeight
from calculate import Calculate
from calculate_multiple import CalculateMultiple
from settings import Settings
from log import Log


def plot_test_dots(stereo_labels, factor=1):
    'Create a stereo test image pair.'
    dot_data = {'x': [10, 10, 90, 88], 'y': [10, 90, 10, 90]}
    offsets = np.array([1, 1, 0, 2]) * factor
    dot_params = {
        'left': {'title_y': 100, 'color': '#1f77b4', 'x_offsets': offsets},
        'right': {'title_y': 90, 'color': '#ff7f0e'},
    }

    def _calc_x(param):
        offsets = param.get('x_offsets', np.zeros_like(dot_data['x']))
        dot_xs = np.array(dot_data['x']) + np.array(offsets)
        return dot_xs, offsets

    plt.figure(figsize=(10, 10))
    for stereo_label in stereo_labels:
        color = dot_params[stereo_label]['color']
        title_y = dot_params[stereo_label]['title_y']
        dot_xs, _ = _calc_x(dot_params[stereo_label])
        plt.plot(dot_xs, dot_data['y'], 'o', ms=100, mew=5, color=color)
        plt.text(50, title_y, stereo_label.upper(),
                 fontsize=20, ha='center', color=color)
    dot_xs, _ = _calc_x(dot_params['right'])
    _, x_offsets = _calc_x(dot_params['left'])
    for dot_x, dot_y, x_offset in zip(dot_xs, dot_data['y'], x_offsets):
        plt.annotate(x_offset, (dot_x, dot_y), (30, 0),
                     fontsize=20, ha='center', va='center',
                     textcoords='offset points',
                     arrowprops={'fill': True, 'color': 'k'})
    plt.xlim(0, 100)
    plt.ylim(0, 100)
    plt.axis('off')
    stereo_label_str = stereo_labels[0] if len(stereo_labels) == 1 else 'both'
    if not os.path.exists('test_images'):
        os.mkdir('test_images')
    plt.savefig(f'test_images/{stereo_label_str}_dots_{factor}.png', dpi=100)
    plt.close()


plot_test_dots(['left'])
plot_test_dots(['right'])
plot_test_dots(['left', 'right'])
OFFSET_FACTOR = 1.5
plot_test_dots(['left'], OFFSET_FACTOR)
plot_test_dots(['right'], OFFSET_FACTOR)


def test_measure_soil_height():
    'Test MeasureSoilHeight.'
    os.environ['CAMERA_CALIBRATION_total_rotation_angle'] = '1'
    os.environ['measure_soil_height_measured_distance'] = '100'
    os.environ['measure_soil_height_calibration_factor'] = '1'
    os.environ['measure_soil_height_verbose'] = '9'
    measure_soil = MeasureSoilHeight()
    measure_soil.capture_images()
    measure_soil.calculate()


def test_calculate(name_id, extension, settings=None, use_assert=True):
    'Test Calculate.'
    if settings is None:
        settings = Settings()
        settings.update('measured_distance', 250)
        settings.update('calibration_factor', 2.2321)
        settings.update('calibration_disparity_offset', 100)
        settings.update('calibration_image_height', 1000)
        settings.update('calibration_image_width', 1000)
        settings.update('verbose', 9)
        settings.update('edit_fbos_config', 1)
    log = Log(settings.settings)
    calculate = Calculate(settings.settings, log)
    calculate.load_images('test_images', name_id, extension)
    details = calculate.calculate()
    soil_z = details['values']['calculated_soil_z']
    if use_assert:
        assert soil_z == -223, soil_z


def test_calculate_set():
    'Test CalculateMultiple.'
    settings = Settings()
    settings.update('measured_distance', 250)
    settings.update('calibration_factor', 0)
    settings.update('calibration_disparity_offset', 0)
    settings.update('verbose', 9)
    settings.update('edit_fbos_config', 1)
    log = Log(settings.settings)
    directory = 'test_images'
    filenames = [{'left': f'{directory}/left_dots_1.png',
                  'right': f'{directory}/right_dots_1.png'},
                 {'left': f'{directory}/left_dots_{OFFSET_FACTOR}.png',
                  'right': f'{directory}/right_dots_{OFFSET_FACTOR}.png'}]
    image_sets = [
        {'left': [{
            'data': cv.imread(filenames[0]['left']),
            'name': filenames[0]['left']}],
         'right': [{
             'data': cv.imread(filenames[0]['right']),
             'name': filenames[0]['right']}]},
        {'left': [{
            'data': cv.imread(filenames[1]['left']),
            'name': filenames[1]['left'],
            'location': {'z': -50}}],
         'right': [{
             'data': cv.imread(filenames[1]['right']),
             'name': filenames[1]['right'],
             'location': {'z': -50}}]},
    ]
    calculations = CalculateMultiple(settings.settings, log, image_sets)
    calculations.calculate_multiple()
    soil_z = calculations.set_results[-1]['values']['calculated_soil_z']
    assert soil_z == -250, soil_z


def test_many(common_id):
    'Test Calculate for each stereo pair in test_images.'
    settings = Settings()
    settings.update('rotation', 0)
    settings.update('rotation_adjustment', 0)
    settings.update('measured_distance', 250)
    settings.update('calibration_factor', 1)
    settings.update('calibration_disparity_offset', 100)
    settings.update('verbose', 9)
    left_files = [i for i in os.listdir('test_images') if i.startswith('left')]
    for left_file in left_files:
        name_w_ext = left_file.split('left_')[1]
        name_id = '.'.join(name_w_ext.split('.')[:-1])
        file_common_id = '_'.join(name_id.split('_')[:1])
        if file_common_id == common_id:
            extension = name_w_ext.split('.')[-1]
            test_calculate(name_id, extension, settings, use_assert=False)


if __name__ == '__main__':
    # test_measure_soil_height()
    test_calculate('dots_1', 'png')
    test_many('dots')
    # test_calculate_set()

#!/usr/bin/env python3

'Run tests.'

import os
import numpy as np
import matplotlib.pyplot as plt
from measure_height import MeasureSoilHeight
from calculate import Calculate
from settings import Settings


def plot_test_dots(stereo_labels):
    'Create a stereo test image pair.'
    dot_data = {'x': [10, 10, 90, 88], 'y': [10, 90, 10, 90]}
    dot_params = {
        'left': {'title_y': 100, 'color': '#1f77b4', 'x_offsets': [1, 1, 0, 2]},
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
    plt.savefig(f'test_images/{stereo_label_str}_dots.png', dpi=100)
    plt.close()


plot_test_dots(['left'])
plot_test_dots(['right'])
plot_test_dots(['left', 'right'])


def test_measure_soil_height():
    'Test MeasureSoilHeight.'
    os.environ['CAMERA_CALIBRATION_total_rotation_angle'] = '1'
    os.environ['measure_soil_height_measured_distance'] = '100'
    os.environ['measure_soil_height_calibration_factor'] = '1'
    os.environ['measure_soil_height_verbose'] = '9'
    measure_soil = MeasureSoilHeight()
    measure_soil.capture_images()
    measure_soil.calculate()


def test_calculate():
    'Test Calculate.'
    settings = Settings()
    settings.update('measured_distance', 250)
    settings.update('calibration_factor', 0)
    settings.update('calibration_image_width', 1000)
    settings.update('calibration_image_height', 1000)
    settings.update('verbose', 9)
    calculate = Calculate(settings.settings)
    calculate.load_images('test_images', 'dots', 'png')
    calculate.calculate()
    factor = settings.settings['calibration_factor']
    assert factor == 2.2321, factor


if __name__ == '__main__':
    # test_measure_soil_height()
    test_calculate()

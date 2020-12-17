#!/usr/bin/env python3.8

'Run tests.'

import os
import sys
from time import time
TIMES = {'start': time()}
if TIMES:
    from measure_height import MeasureSoilHeight
    from tests.mocks import MockDevice, MockTools, MockCV
    from tests.runner import TestRunner, print_title
TIMES['imports_done'] = time()


def _result_log(soil_z):
    return {
        'message': f'Soil height saved: {soil_z}',
        'args': (),
        'kwargs': {
            'message_type': 'success',
            'channels': ['toast'],
        },
    }


def _point(soil_z):
    return {
        'pointer_type': 'GenericPointer',
        'name': 'Soil Height',
        'x': 0.0,
        'y': 0.0,
        'z': soil_z,
        'radius': 0,
        'meta': {
            'created_by': 'measure-soil-height',
            'at_soil_level': 'true',
            'color': 'gray',
        }
    }


def test_calibration():
    'Test MeasureSoilHeight calibration.'
    print_title('MeasureSoilHeight calibration', char='|')
    os.environ['measure_soil_height_measured_distance'] = '100'
    os.environ['measure_soil_height_repeat_capture_delay_s'] = '0'
    os.environ['measure_soil_height_verbose'] = '5'
    measure_soil = MeasureSoilHeight()
    measure_soil.device = MockDevice()
    measure_soil.core.tools.device = MockDevice()
    measure_soil.core.settings.init_device_settings()
    measure_soil.log.device = MockDevice()
    measure_soil.core.results.tools = MockTools()
    measure_soil.cv = MockCV()
    measure_soil.capture_images()
    measure_soil.calculate()
    coords = measure_soil.device.position_history
    assert coords == [
        {'x': 0, 'y': 0, 'z': 0},
        {'x': 0, 'y': 10, 'z': 0},
        {'x': 0, 'y': 10, 'z': -50},
        {'x': 0, 'y': 0, 'z': -50},
        {'x': 0, 'y': 0, 'z': 0},
    ], coords
    logs = measure_soil.log.device.log_history
    assert logs == [_result_log(-99)], logs
    envs = measure_soil.core.results.tools.config_history
    assert envs == [
        ['disparity_search_depth', 2],
        ['calibration_factor', 0.3147],
        ['calibration_disparity_offset', 159.78125],
        ['calibration_image_width', 100],
        ['calibration_image_height', 100],
        ['calibration_measured_at_z', 0.0],
        ['calibration_maximum', 164],
    ], envs
    posts = measure_soil.core.results.tools.post_history
    assert posts == [['points', _point(-99)]], posts
    pins = measure_soil.device.pin_history
    assert pins == [], pins
    count = measure_soil.cv.capture_count
    assert count == 44, count


def test_measure_soil_height():
    'Test MeasureSoilHeight.'
    print_title('MeasureSoilHeight', char='|')
    os.environ['measure_soil_height_measured_distance'] = '100'
    os.environ['measure_soil_height_calibration_factor'] = '1'
    os.environ['measure_soil_height_calibration_disparity_offset'] = '160'
    os.environ['measure_soil_height_repeat_capture_delay_s'] = '0'
    os.environ['measure_soil_height_verbose'] = '5'
    os.environ['measure_soil_height_log_verbosity'] = '2'
    measure_soil = MeasureSoilHeight()
    measure_soil.device = MockDevice()
    measure_soil.core.tools.device = MockDevice()
    measure_soil.core.settings.init_device_settings()
    measure_soil.log.device = MockDevice()
    measure_soil.core.results.tools = MockTools()
    measure_soil.cv = MockCV()
    measure_soil.capture_images()
    measure_soil.calculate()
    coords = measure_soil.device.position_history
    assert coords == [
        {'x': 0, 'y': 0, 'z': 0},
        {'x': 0, 'y': 10, 'z': 0},
        {'x': 0, 'y': 0, 'z': 0},
    ], coords
    logs = measure_soil.log.device.log_history
    assert logs == [
        {'message': '[Measure Soil Height] Capturing left image...',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
        {'message': '[Measure Soil Height] Capturing right image...',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
        {'message': '[Measure Soil Height] Returning to starting position...',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
        {'message': '[Measure Soil Height] Checking images...',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
        {'message': '[Measure Soil Height] Checking image angle...',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
        {'message': '[Measure Soil Height] Calculating disparity...',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
        {'message': '[Measure Soil Height] Soil z range: -102 to -98',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
        _result_log(-100),
        {'message': '[Measure Soil Height] Saving output images...',
         'args': (),
         'kwargs': {'message_type': 'debug', 'channels': None}},
    ], logs
    envs = measure_soil.core.results.tools.config_history
    assert envs == [['disparity_search_depth', 2]], envs
    posts = measure_soil.core.results.tools.post_history
    assert posts == [['points', _point(-100)]], posts
    pins = measure_soil.device.pin_history
    assert pins == [], pins
    count = measure_soil.cv.capture_count
    assert count == 22, count
    params = measure_soil.cv.parameter_history
    assert params == {'width': 640, 'height': 480}, params


def test_calculate_multiple():
    'Test CalculateMultiple.'
    print_title('CalculateMultiple', char='_')
    os.environ.clear()
    runner = TestRunner()
    runner.pre_times = TIMES
    runner.verbosity = 5
    runner.test_data_sets()
    return not runner.status_ok


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        for filename in os.listdir('results'):
            os.remove(f'results/{filename}')
    test_calibration()
    test_measure_soil_height()
    failure = test_calculate_multiple()
    sys.exit(bool(failure))

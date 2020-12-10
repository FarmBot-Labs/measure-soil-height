#!/usr/bin/env python3.8

'Run tests.'

import os
import sys
from time import time
TIMES = {'start': time()}
if TIMES:
    from measure_height import MeasureSoilHeight
    from tests.mocks import MockDevice, MockCV
    from tests.runner import TestRunner, print_title
TIMES['imports_done'] = time()


def test_measure_soil_height():
    'Test MeasureSoilHeight.'
    print_title('MeasureSoilHeight', char='|')
    os.environ['CAMERA_CALIBRATION_total_rotation_angle'] = '0'
    os.environ['measure_soil_height_measured_distance'] = '100'
    os.environ['measure_soil_height_calibration_factor'] = '1'
    os.environ['measure_soil_height_repeat_capture_delay_s'] = '0'
    os.environ['measure_soil_height_verbose'] = '5'
    measure_soil = MeasureSoilHeight()
    measure_soil.device = MockDevice()
    measure_soil.cv = MockCV()
    measure_soil.capture_images()
    measure_soil.calculate()
    coords = measure_soil.device.position_history
    assert coords == [
        {'x': 0, 'y': 0, 'z': 0},
        {'x': 0, 'y': 10, 'z': 0},
        {'x': 0, 'y': 0, 'z': 0},
    ], coords
    logs = measure_soil.device.log_history
    assert logs == [], logs
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
    test_measure_soil_height()
    failure = test_calculate_multiple()
    sys.exit(bool(failure))

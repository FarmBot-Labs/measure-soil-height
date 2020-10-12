#!/usr/bin/env python3

'''Measure soil z height using OpenCV and FarmBot's current position.'''

import os
import sys
import cv2
import numpy as np
from farmware_tools import app, device, get_config_value, set_config_value, env

FARMWARE_NAME = 'Measure Soil Height'


def get_config(key):
    'Get config input.'
    return get_config_value(FARMWARE_NAME, key, float)


def error(message):
    'Send error message.'
    device.log(message, 'error')
    sys.exit(1)


def capture():
    'Capture grayscale image and adjust rotation.'
    camera = cv2.VideoCapture(0)
    ret, image = camera.read()

    if not ret:
        device.log('Problem getting image.', 'error')
        sys.exit(1)

    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image = cv2.medianBlur(image, 5)

    height, width = image.shape
    center = int(width / 2), int(height / 2)
    rotation_key = 'CAMERA_CALIBRATION_total_rotation_angle'
    rotation = float(os.getenv(rotation_key, '0'))
    matrix = cv2.getRotationMatrix2D(center, rotation, 1)
    image = cv2.warpAffine(image, matrix, (width, height))

    return image


class MeasureSoilHeight():
    'Measure soil z height.'

    def __init__(self):
        self.measured_distance = get_config('measured_distance')
        self.calibration_factor = get_config('calibration_factor')
        self.current_position = device.get_current_position()
        firmware_params = device.get_bot_state().get('mcu_params', {})
        negative_z = firmware_params.get('movement_home_up_z', 1)
        self.z_sign = -1 if negative_z else 1
        self.images = []
        self.soil_z = None

    def calculate_soil_height(self):
        'Calculate soil height.'
        stereo = cv2.StereoBM().create()
        disparity = stereo.compute(self.images[0], self.images[1])
        cv2.imwrite(f'{env.Env().images_dir}/disparity_map.png', disparity)
        total = 0
        values = []
        for j in disparity:
            for k in j:
                total += 1
                if k > 0:
                    values.append(k)
        mean_disparity = np.mean(values)
        avg = mean_disparity
        cov = len(values) / float(total) * 100
        device.log(f'Average disparity: {avg:.0f} ({cov:.0f}% coverage)')
        if self.calibration_factor == 0:
            factor = round(self.measured_distance / mean_disparity, 2)
            set_config_value(FARMWARE_NAME, 'calibration_factor', factor)
            self.calibration_factor = factor
        distance = mean_disparity * self.calibration_factor
        current_z = float(self.current_position.get('z', 0))
        self.soil_z = int(current_z + self.z_sign * distance)
        self.save_soil_height()

    def run(self):
        'Capture stereo images, calculate soil height, and save to account.'
        if self.measured_distance == 0 and self.calibration_factor == 0:
            error('Initial calibration measured distance input required.')

        self.images.append(capture())
        device.move_relative(0, 5, 0, speed=100)
        self.images.append(capture())

        device.move_relative(0, -5, 0, speed=100)

        self.calculate_soil_height()

    def save_soil_height(self):
        'Save soil height.'
        app.patch('fbos_config', payload={'soil_height': self.soil_z})
        app.post('points', {
            'pointer_type': 'GenericPointer',
            'name': 'Soil Height',
            'x': self.current_position.get('x'),
            'y': self.current_position.get('y'),
            'z': self.soil_z,
            'radius': 0,
            'meta': {
                'created_by': 'measure-soil-height',
                'color': 'gray',
            },
        })
        device.log(f'{self.soil_z:.0f} soil height saved.', 'success')


if __name__ == '__main__':
    measure_soil = MeasureSoilHeight()
    measure_soil.run()

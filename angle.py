#!/usr/bin/env python3.8

'Angle determination.'

import numpy as np
import cv2 as cv


class Angle():
    'Calculate camera angle.'

    def __init__(self, settings, log, images):
        self.settings = settings
        self.log = log
        self.images = images
        self.deltas = None
        self.angle = None
        self.mask = None

    def _calculate_initial_angle(self):
        x_deltas = self.deltas['x']
        y_deltas = self.deltas['y']
        y_deltas[y_deltas == 0] = 1
        angles_data = np.degrees(np.arctan(x_deltas / y_deltas))
        angles_data[y_deltas == 0] = np.nan
        angles_img = angles_data.copy()
        angles_img[angles_img > 89] = 0
        angles_img[angles_img < 0] += 90
        self.images.output_init(angles_img, 'angles')
        angles = self.images.output['angles']
        self.log.debug(angles.data.report['report'])
        self.angle = angles.data.reduced['stats']['mid']
        self.mask = angles.data.reduced['masks']['mid']
        if angles.data.reduced['stats']['mid_size_p'] < 3:
            msg = f'Mixed angles. Using 0 instead of {self.angle:.1f}'
            self.log.debug(msg)
            self.angle = 0
            self.mask = ((angles_data > self.angle - 1)
                         * (angles_data < self.angle + 1))

    @staticmethod
    def rotate_vector(vector, angle):
        'Rotate a vector.'
        matrix = cv.getRotationMatrix2D((0, 0), -angle, 1)[:, :2]
        return np.dot(matrix, vector)

    def _adjust_angle(self):
        delta = [self._get_delta('x'), self._get_delta('y')]
        delta_log = f'rotation [dx, dy]: 0 {np.around(delta, 2)}'
        rotated_delta = self.rotate_vector(delta, self.angle)
        delta_log += f' -> {self.angle:.2f} {np.around(rotated_delta, 2)}'
        if abs(rotated_delta[1]) > abs(rotated_delta[0]):
            self.angle += 90
        rotated_delta = self.rotate_vector(delta, self.angle)
        delta_log += f' -> {self.angle:.2f} {np.around(rotated_delta, 2)}'
        if rotated_delta[0] > 0:
            self.angle += 180
        rotated_delta = self.rotate_vector(delta, self.angle)
        delta_log += f' -> {self.angle:.2f} {np.around(rotated_delta, 2)}'
        self.log.debug(delta_log)
        if self.angle > 180:
            self.angle -= 360
        return self.angle

    def _get_delta(self, axis):
        values = self.deltas[axis].copy()
        values[np.invert(self.mask)] = np.nan
        values[abs(values) < 0.5] = np.nan
        tag = f'd{axis}'
        self.images.output_init(values, tag, reduce=False)
        delta_data = self.images.output[tag]
        delta_data.reduce_data(no_threshold=True)
        avg = delta_data.data.reduced['stats']['mid']
        if delta_data.data.reduced['stats']['mid_size_p'] < 3:
            self.log.debug(f'Small {tag} sample. Using 0 instead of {avg:.1f}')
            avg = 0
        if abs(avg) <= 1:
            avg = 0
        return avg

    def _compare_angles(self):
        self.log.debug('Checking image angle...', verbosity=2)
        settings = self.settings
        self._calculate_initial_angle()
        self._adjust_angle()
        angle_adjust_key = 'calibration_rotation_adjustment'
        provided = settings['rotation'] + settings[angle_adjust_key]
        msg = f'Using {self.angle:.1f} camera angle'
        if (self.angle - provided) > 0.1:
            msg += f' instead of {provided}'
        self.log.debug(msg)
        self.angle = round(self.angle, 1)
        missing_adjust = settings['calibration_rotation_adjustment'] == 0
        if missing_adjust:
            settings[angle_adjust_key] = settings['rotation'] - self.angle

    def calculate(self):
        'Calculate angle using optical flow.'
        input_images = [self.images.input['left'][0],
                        self.images.input['right'][0]]
        image0 = input_images[0].preprocess(perform_rotation=False)
        image1 = input_images[1].preprocess(perform_rotation=False)
        flow = cv.FarnebackOpticalFlow_create()
        results = flow.calc(image0, image1, None)
        results = self.images.filter_plants(results)
        self.deltas = {'x': results[:, :, 0], 'y': results[:, :, 1]}
        self._compare_angles()
        disparity_data_floats = np.hypot(self.deltas['x'], self.deltas['y'])
        disparity_data = np.int32(disparity_data_floats * 16)
        self.log.debug(f'{disparity_data.min() = } {disparity_data.max() = }')
        self.images.output_init(disparity_data, 'disparity_from_flow')

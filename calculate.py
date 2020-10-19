#!/usr/bin/env python3

'Calculations for MeasureSoilHeight.'

import numpy as np
import cv2 as cv
from log import Log
from data import Data
from results import Results
from histogram import Histogram


def rotate(image, degrees):
    'Rotate image.'
    height, width = image.shape[:2]
    center = int(width / 2), int(height / 2)
    matrix = cv.getRotationMatrix2D(center, degrees, 1)
    image = cv.warpAffine(image, matrix, (width, height))
    return image


def odd(number):
    'Ensure number is odd.'
    if number % 2 == 0:
        number += 1
    return number


class Calculate():
    'Calculate results.'

    def __init__(self, settings, images=None):
        self.settings = settings
        self.log = Log(settings)
        self.input_images = images or {'left': [], 'right': []}
        self.base_image = None
        self.base_name = None
        if images:
            self._set_base_image()
        self.output_images = {}
        self.results = Results(settings)

    def load_images(self, directory, name, ext):
        'Load `left_name.ext` and `right_name.ext` stereo images from file.'
        for stereo_id in ['left', 'right']:
            filepath = f'{directory}/{stereo_id}_{name}.{ext}'
            self.input_images[stereo_id] = [
                {'name': filepath, 'data': cv.imread(filepath)},
            ]
        self._set_base_image()

    def _set_base_image(self):
        self.base_image = self.input_images['left'][0]
        self.base_name = self.base_image['name'].split('/')[-1].split('.')[0]
        if 'left_' in self.base_name:
            self.base_name = self.base_name.split('left_')[1]

    def check_images(self):
        'Check capture images.'
        for stereo_id, images in self.input_images.items():
            for i, image in enumerate(images):
                if image['data'] is None:
                    self.log.error('Image missing.')
                image_id = f'{stereo_id}_{i}' if len(images) > 1 else stereo_id
                image['reduced'] = Data(image['data'], image_id, self.settings)
                content = image['reduced'].report
                self.log.debug(content['report'])
                if self.settings['verbose'] > 3:
                    filename = f'{image_id}_{self.base_name}'
                    self.results.save_image(filename, image['data'])
                if content['coverage'] < self.settings['input_coverage_threshold']:
                    self.log.error('Not enough detail. Check recent images.')

    def get_image_size(self):
        'Get image height and width.'
        return self.input_images['left'][0]['data'].shape[:2]

    def _validate_calibration_data(self):
        calibrated_width = self.settings['calibration_image_width']
        calibrated_height = self.settings['calibration_image_height']
        height, width = self.get_image_size()
        width_mismatch = calibrated_width and calibrated_width != width
        height_mismatch = calibrated_height and calibrated_height != height
        if width_mismatch and height_mismatch:
            self.log.error('Image size must match calibration.')

    def calculate_soil_z(self, disparity_value):
        'Calculate soil z from disparity value.'
        calibration_factor = self.settings['calibration_factor']
        z_sign = -1 if self.settings['negative_z'] else 1
        if calibration_factor == 0:
            return None
        self._validate_calibration_data()
        distance = disparity_value * calibration_factor
        current_z = float(self.settings['initial_position'].get('z', 0))
        return int(current_z + z_sign * distance)

    def _preprocess(self, image):
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        blur = odd(self.settings['blur'])
        blurred = cv.medianBlur(gray, blur) if blur else gray
        rotated = rotate(blurred, self.settings['rotation'])
        return rotated

    def _combine_disparity(self, stereo):
        disparities = []
        for j, left_image in enumerate(self.input_images['left']):
            for k, right_image in enumerate(self.input_images['right']):
                left = self._preprocess(left_image['data'])
                right = self._preprocess(right_image['data'])
                result = stereo.compute(left, right)
                multiple = len(self.input_images['left']) > 1
                if self.settings['verbose'] > 3 and multiple:
                    normalized = self._normalize_disparity(result)
                    self._save_image(f'depth_map_bw_{j}_{k}', normalized)
                disparities.append(result)
        disparity_data = disparities[0]
        for computed in disparities[1:]:
            mask = disparity_data < self.settings['pixel_value_threshold']
            disparity_data[mask] = computed[mask]
        return disparity_data

    def calculate_disparity(self):
        'Calculate and reduce disparity data.'
        num_disparities = int(16 * self.settings['disparity_search_depth'])
        block_size_setting = int(self.settings['disparity_block_size'])
        block_size = min(max(5, odd(block_size_setting)), 255)
        stereo = cv.StereoBM().create(num_disparities, block_size)
        disparity_data = self._combine_disparity(stereo)
        self.output_images['disparity'] = Data(
            disparity_data, 'disparity', self.settings)
        self.save_disparity()

    @staticmethod
    def _normalize_disparity(disparity):
        return (disparity.clip(0) / disparity.max() * 255).astype(np.uint8)

    def _colorize_disparity(self):
        colorized = np.dstack([self.output_images['depth_map_bw']] * 3)
        disparity = self.output_images['disparity']
        reduced = disparity.reduced
        colorized[reduced['history'][-2]['masks']['low']] = [100, 100, 155]
        colorized[reduced['history'][-2]['masks']['high']] = [100, 100, 255]
        colorized[reduced['masks']['mid']] = [100, 255, 100]
        colorized[disparity.data < 0] = [0, 0, 0]
        self.output_images['disparity_map'] = colorized

    def _save_image(self, name, img):
        filename = f'{self.base_name}_{name}'
        self.results.save_image(filename, img)

    def save_disparity(self):
        'Save disparity map.'
        images = self.output_images
        data = images['disparity'].data
        reduced = images['disparity'].reduced
        if data.max() < 1:
            self.log.error('Zero disparity.')
        images['depth_map_bw'] = self._normalize_disparity(data)
        self._colorize_disparity()

        base_img = self.base_image['data']
        rotation = self.settings['rotation']
        if self.settings['verbose'] > 2:
            unrotated = rotate(images['depth_map_bw'], -rotation)
            self._save_image('depth_map_bw', unrotated)
        if self.settings['verbose'] > 3:
            unrotated = rotate(images['disparity_map'], -rotation)
            self._save_image('disparity_map', unrotated)
            calculate_soil_z = self.calculate_soil_z
            histogram = Histogram(data, reduced, calculate_soil_z).generate()
            self._save_image('histogram', histogram)
            img_hist = Histogram(base_img, self.base_image['reduced'].reduced,
                                 calculate_soil_z, simple=True).generate()
            self._save_image('img_histogram', img_hist)
        alpha = self.settings['image_blend_percent'] / 100.
        color_dp = rotate(images['disparity_map'], -rotation)
        img = cv.addWeighted(base_img, alpha, color_dp, 1 - alpha, 0)
        if self.settings['verbose'] > 1 and not self.settings['verbose'] == 3:
            self._save_image('depth_map', img)

    def calculate(self):
        'Calculate disparity, calibration factor, and soil height.'
        self.check_images()

        measured_distance = self.settings['measured_distance']
        missing_measured_distance = measured_distance == 0
        missing_calibration_factor = self.settings['calibration_factor'] == 0
        if missing_measured_distance and missing_calibration_factor:
            self.log.error(
                'Initial calibration measured distance input required.')

        self.calculate_disparity()
        disparity = self.output_images['disparity'].report
        self.log.debug(disparity['report'])
        disparity_log = f'Average disparity: {disparity["mid"]} '
        disparity_log += f'{disparity["coverage"]}% coverage'
        self.log.debug(disparity_log)
        if disparity['coverage'] < self.settings['disparity_coverage_threshold']:
            self.log.error(
                'Not enough disparity information. Check recent images.')

        if missing_calibration_factor:
            factor = round(measured_distance / disparity['mid'], 4)
            height, width = self.get_image_size()
            self.results.set_calibration_factor(factor, height, width)

        soil_z = self.calculate_soil_z(disparity['mid'])
        self.results.save_soil_height(soil_z)

        self.results.save_report(
            self.base_name, self.output_images, self.input_images)

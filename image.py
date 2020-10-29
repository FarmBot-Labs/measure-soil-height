#!/usr/bin/env python3.8

'Image processing.'

import numpy as np
import cv2 as cv
from data import Data
from histogram import Histogram, FONT, WHITE


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


def shape(image):
    'Get image shape properties.'
    height, width = image.shape[:2]
    return {'width': width, 'height': height}


def create_output_collage(all_images, soil_z):
    'Save rotated images, depth maps, and histograms to a single image.'
    image_0 = all_images[0][0]
    collage = _concat_images(all_images, np.max(image_0.shape[:2]))
    if soil_z is not None:
        middle = int(np.max(image_0.shape[:2]) * 3 / 2.1)
        collage = cv.putText(collage, f'{soil_z= } mm',
                             (middle, middle * 2), FONT, 5, WHITE, 4)
    return collage


def _concat_images(all_images, cell_size):
    height = len(all_images)
    width = len(all_images[0])
    size = np.append(np.multiply((height, width), cell_size), 3)
    collage = np.zeros(size, np.uint8)
    for row_index, row_images in enumerate(all_images):
        for col_index, original in enumerate(row_images):
            aspect = shape(original)['width'] / shape(original)['height']
            new_size = (cell_size, int(cell_size / aspect))
            resized = cv.resize(original, new_size)
            start = {'y': row_index * cell_size,
                     'x': col_index * cell_size}
            end = {'y': start['y'] + shape(resized)['height'],
                   'x': start['x'] + shape(resized)['width']}
            collage[start['y']:end['y'], start['x']:end['x']] = resized
    return collage


class Image():
    'Process image data.'

    def __init__(self, settings, results, image=None, info=None):
        self.settings = settings
        self.results = results
        self.image = image.copy()
        self.info = info
        self.viewer = False
        self.data = None
        self.histogram = None

    def reduce_data(self):
        'Generate reduced data.'
        self.data = Data(self.image, self.info, self.settings)

    def rotate_copy(self, image=None, direction=1):
        'Return rotated image.'
        if image is None:
            image = self.image
        initial_rotation = self.settings['rotation']
        rotation_adjustment = self.settings['rotation_adjustment']
        angle = initial_rotation + rotation_adjustment
        return rotate(image, direction * angle)

    def rotate(self, direction=1):
        'Rotate image.'
        self.image = self.rotate_copy(direction=direction)

    def preprocess(self):
        'Return pre-processed image.'
        self.show()
        image = self.image.copy()
        gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        blur = odd(self.settings['blur'])
        blurred = cv.medianBlur(gray, blur) if blur else gray
        rotated = self.rotate_copy(blurred)
        self.show(rotated)
        return rotated

    def normalize(self):
        'Normalize image values.'
        normalized = self.image.clip(0) / self.image.max() * 255
        self.image = normalized.astype(np.uint8)

    def channel3(self):
        'Ensure 3 channels in image.'
        if len(self.image.shape) < 3:
            self.image = np.dstack([self.image] * 3)

    def colorize_depth(self, disparity):
        'Colorize depth data according to reduced data statistics.'
        self.channel3()
        self.show()
        reduced = disparity.reduced
        idx = -2 if len(reduced['history']) > 1 else -1
        self.image[reduced['history'][idx]['masks']['low']] = [100, 100, 155]
        self.image[reduced['history'][idx]['masks']['high']] = [100, 100, 255]
        self.image[reduced['masks']['mid']] = [100, 255, 100]
        self.image[disparity.data < 0] = [0, 0, 0]
        self.show()

    def blend_with(self, image_b):
        'Blend two images together according to alpha setting.'
        alpha = self.settings['image_blend_percent'] / 100.
        self.image = cv.addWeighted(self.image, alpha, image_b, 1 - alpha, 0)

    def add_soil_z_annotation(self, soil_z):
        'Add the soil z height value to the image center.'
        if self.settings['image_annotate_soil_z']:
            height = shape(self.image)['height']
            width = shape(self.image)['width']
            center_y = int(height / 2 - 0.1 * height)
            center_x = int(width / 2 - 0.1 * width)
            center = (center_y, center_x)

            def _add_text(color, thickness):
                if soil_z is not None:
                    self.image = cv.putText(self.image, str(soil_z),
                                            center, FONT, 5, color, thickness)
            _add_text((0, 0, 0), 10)
            _add_text(WHITE, 3)

    def show(self, image=None):
        'If enabled, open image in viewer.'
        if not self.viewer:
            return
        if image is None:
            image = self.image
        cv.imshow('', image)
        cv.waitKey()

    def create_histogram(self, calc_z, simple=False):
        'Generate histogram.'
        self.histogram = Histogram(self.data, calc_z, simple=simple)
        self.show(self.histogram.histogram)

    def save_histogram(self, name):
        'Save histogram.'
        filename = f'{self.info["base_name"]}_{name}'
        self.results.save_image(filename, self.histogram.histogram)

    def save(self, name):
        'Save image to file.'
        filename = f'{self.info["base_name"]}_{name}'
        self.results.save_image(filename, self.image)

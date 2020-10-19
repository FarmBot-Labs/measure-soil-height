#!/usr/bin/env python3

'''Measure soil z height using OpenCV and FarmBot's current position.'''

from time import time, sleep
import cv2 as cv
from farmware_tools import device
from log import Log
from settings import Settings
from results import Results
from calculate import Calculate


class MeasureSoilHeight():
    'Measure soil z height.'

    def __init__(self):
        self.settings = Settings().settings
        self.images = {'left': [], 'right': []}
        self.log = Log(self.settings)

    def capture(self, port, timestamp):
        'Capture image with camera.'
        camera = cv.VideoCapture(port)
        camera.set(cv.CAP_PROP_FRAME_WIDTH, self.settings['capture_width'])
        camera.set(cv.CAP_PROP_FRAME_HEIGHT, self.settings['capture_height'])
        ret, image = camera.read()
        if not ret:
            self.log.error('Problem getting image.')
        return {'data': image, 'name': timestamp}

    def capture_images(self):
        'Capture stereo images, calculate soil height, and save to account.'
        timestamp = str(int(time()))
        port = int(self.settings['camera_port'])
        y_offset = self.settings['image_offset_mm']
        location_capture_count = self.settings['capture_count_at_each_location']
        repeat_capture_delay = self.settings['repeat_capture_delay_s']

        image_order = ['left', 'right']
        if self.settings['reverse_image_order']:
            image_order = image_order[::-1]

        self.log.debug(f'Capturing {image_order[0]} image...')
        self.images[image_order[0]].append(self.capture(port, timestamp))
        for _ in range(location_capture_count - 1):
            sleep(repeat_capture_delay)
            self.images[image_order[0]].append(self.capture(port, timestamp))

        device.move_relative(x=0, y=y_offset, z=0, speed=100)

        self.log.debug(f'Capturing {image_order[1]} image...')
        for _ in range(location_capture_count):
            sleep(repeat_capture_delay)
            self.images[image_order[1]].append(self.capture(port, timestamp))

        self.log.debug('Returning to starting position...')
        device.move_relative(x=0, y=-y_offset, z=0, speed=100)

    def save_captured_images(self):
        'Save input images.'
        results = Results(self.settings)
        for stereo_id, images in self.images.items():
            name = images[0]['name']
            image = images[0]['data']
            results.save_image(f'{stereo_id}_{name}', image)

    def calculate(self):
        'Calculate soil height.'
        Calculate(self.settings, self.images).calculate()


if __name__ == '__main__':
    measure_soil = MeasureSoilHeight()
    measure_soil.capture_images()
    measure_soil.calculate()

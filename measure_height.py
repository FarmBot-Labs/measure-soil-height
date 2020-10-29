#!/usr/bin/env python3.8

'''Measure soil z height using OpenCV and FarmBot's current position.'''

from time import time, sleep
import cv2 as cv
from farmware_tools import device
from serial_device import SerialDevice
from log import Log
from settings import Settings
from results import Results
from calculate_multiple import CalculateMultiple


class MeasureSoilHeight():
    'Measure soil z height.'

    def __init__(self):
        self.settings = Settings().settings
        self.images = []
        self.log = Log(self.settings)
        self.results = Results(self.settings, self.log)
        if self.settings['use_serial']:
            self.log.debug('Setting up serial connection...')
            self.device = SerialDevice(self.settings)
        else:
            self.device = device

    def capture(self, port, timestamp, stereo_id):
        'Capture image with camera.'
        camera = cv.VideoCapture(port)
        camera.set(cv.CAP_PROP_FRAME_WIDTH, self.settings['capture_width'])
        camera.set(cv.CAP_PROP_FRAME_HEIGHT, self.settings['capture_height'])
        for _ in range(10):
            camera.grab()
            sleep(0.1)
        ret, image = camera.read()
        if not ret:
            self.log.error('Problem getting image.')
        location = self.device.get_current_position()
        if self.settings['capture_only']:
            self.results.save_image(f'{stereo_id}_{timestamp}', image)
        return {'data': image, 'tag': stereo_id,
                'name': timestamp, 'location': location}

    def location_captures(self, i, stereo_id, timestamp):
        'Capture images at position.'
        self.log.debug(f'Capturing {stereo_id} image...')
        port = int(self.settings['camera_port'])
        for _ in range(self.settings['capture_count_at_each_location']):
            sleep(self.settings['repeat_capture_delay_s'])
            capture_data = self.capture(port, timestamp, stereo_id)
            self.images[i][stereo_id].append(capture_data)

    def capture_images(self):
        'Capture stereo images, calculate soil height, and save to account.'
        if self.settings['use_lights']:
            self.device.write_pin(7, 1, 0)

        needs_calibration = self.settings['calibration_factor'] == 0
        use_sets = needs_calibration or self.settings['force_sets']
        sets = self.settings['number_of_stereo_sets'] if use_sets else 1
        image_order = ['left', 'right']
        if self.settings['reverse_image_order']:
            image_order = image_order[::-1]
        speed = self.settings['movement_speed_percent']
        to_start = {'x': 0, 'y': 0, 'z': 0}

        flip = True
        for i in range(sets):
            self.images.append({'left': [], 'right': []})
            timestamp = str(int(time()))

            if i > 0:
                z_direction = -1 if self.settings['negative_z'] else 1
                z_relative = z_direction * self.settings['set_offset_mm']
                to_start['z'] -= z_relative
                self.device.move_relative(x=0, y=0, z=z_relative, speed=speed)
            stereo_id = image_order[int(not flip)]
            self.location_captures(i, stereo_id, timestamp)

            y_relative = self.settings['stereo_y'] * (1 if not flip else -1)
            to_start['y'] += y_relative
            self.device.move_relative(x=0, y=-y_relative, z=0, speed=speed)
            stereo_id = image_order[int(flip)]
            self.location_captures(i, stereo_id, timestamp)
            flip = not flip

        if self.settings['use_lights']:
            self.device.write_pin(7, 0, 0)
        self.log.debug('Returning to starting position...')
        self.device.move_relative(
            x=to_start['x'],
            y=to_start['y'],
            z=to_start['z'], speed=speed)

    def calculate(self):
        'Calculate soil height.'
        if not self.settings['capture_only']:
            calculations = CalculateMultiple(
                self.settings, self.log, self.images)
            calculations.calculate_multiple()


if __name__ == '__main__':
    measure_soil = MeasureSoilHeight()
    measure_soil.capture_images()
    measure_soil.calculate()

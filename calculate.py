#!/usr/bin/env python3.8

'Calculations.'

import cv2 as cv
from results import Results
from image import Image, shape, odd, create_output_collage


class Calculate():
    'Calculate results.'

    def __init__(self, settings, log, images=None):
        self.settings = settings
        self.log = log
        self.results = Results(settings, log)
        self.input_images = images or {'left': [], 'right': []}
        self.base_name = None
        self.z_info = None
        if images:
            self._set_base_name()
            self._set_z_info()
        for stereo_id, image_infos in self.input_images.items():
            for i, info in enumerate(image_infos):
                image = info.pop('data')
                if image is None:
                    self.log.error('Image missing.')
                self.input_images[stereo_id][i] = self.init_img(image, info)
        self.output_images = {}

    def _set_base_name(self, after_init=False):
        left = self.input_images['left'][0]
        if after_init:
            left = left.info
        base_name = left['name'].split('/')[-1]
        if '.' in base_name:
            base_name = '.'.join(base_name.split('.')[:-1])
        self.base_name = base_name
        if 'left_' in self.base_name:
            self.base_name = self.base_name.split('left_')[1]

    def _set_z_info(self, after_init=False):
        left = self.input_images['left'][0]
        if after_init:
            left = left.info
        image_z = (left.get('location', {}) or {}).get('z')
        initial_z = self.settings['initial_position'].get('z', 0)
        current_z = float(image_z or initial_z)
        self.z_info = {
            'offset': abs(self.settings['calibration_measured_at_z'] - current_z),
            'direction': -1 if self.settings['negative_z'] else 1,
            'current': current_z,
        }

    def init_img(self, image, info=None):
        'Initialize image.'
        if info is None:
            info = {}
        info['base_name'] = self.base_name
        return Image(self.settings, self.results, image=image, info=info)

    def load_images(self, directory, name, ext):
        'Load `left_name.ext` and `right_name.ext` stereo images from file.'
        for stereo_id in ['left', 'right']:
            filepath = f'{directory}/{stereo_id}_{name}.{ext}'
            info = {'tag': stereo_id, 'name': filepath}
            image = cv.imread(filepath)
            if image is None:
                self.log.error('Image missing.')
            self.input_images[stereo_id] = [self.init_img(image, info=info)]
        self._set_base_name(after_init=True)
        self._set_z_info(after_init=True)

    def check_images(self):
        'Check capture images.'
        for stereo_id, images in self.input_images.items():
            for i, image in enumerate(images):
                if image.image is None:
                    self.log.error('Image missing.')
                image_id = f'{stereo_id}_{i}' if len(images) > 1 else stereo_id
                image.reduce_data()
                content = image.data.report
                self.log.debug(content['report'])
                if self.settings['verbose'] > 3 and self.settings['verbose'] != 5:
                    filename = f'{image_id}_{self.base_name}'
                    self.results.save_image(filename, image.image)
                if content['coverage'] < self.settings['input_coverage_threshold']:
                    self.log.error('Not enough detail. Check recent images.')

    def _validate_calibration_data(self):
        calibrated = {
            'width': self.settings['calibration_image_width'],
            'height': self.settings['calibration_image_height']}
        current = shape(self.input_images['left'][0].image)
        mismatch = {k: (v and v != current[k]) for k, v in calibrated.items()}
        if any(mismatch.values()):
            self.log.error('Image size must match calibration.')

    def _z_at_dist(self, distance, z_reference=None):
        if z_reference is None:
            z_reference = self.z_info['current']
        return int(z_reference + self.z_info['direction'] * distance)

    def calculate_soil_z(self, disparity_value):
        'Calculate soil z from disparity value.'
        measured_distance = self.settings['measured_distance']
        measured_at_z = self.settings['calibration_measured_at_z']
        measured_soil_z = self._z_at_dist(measured_distance, measured_at_z)
        disparity_offset = self.settings['calibration_disparity_offset']
        calibration_factor = self.settings['calibration_factor']
        current_z = self.z_info['current']
        direction = self.z_info['direction']
        if calibration_factor == 0:
            return None, []
        self._validate_calibration_data()
        disparity_delta = disparity_value - disparity_offset
        distance = measured_distance - disparity_delta * calibration_factor
        calculated_soil_z = self._z_at_dist(distance)
        calcs = [''] * 4
        calcs[0] += f'({measured_soil_z   = :<7}) = '
        calcs[0] += f'({measured_at_z = :<7})'
        calcs[0] += f' + {direction} * ({measured_distance = })'
        calcs[1] += f'({disparity_delta   = :<7.1f}) = '
        calcs[1] += f'({disparity_value = :<7}) - ({disparity_offset = })'
        calcs[2] += f'({distance          = :<7.1f}) = '
        calcs[2] += f'({measured_distance = :<7})'
        calcs[2] += f' - ({disparity_delta = :.1f}) * ({calibration_factor = })'
        calcs[3] += f'({calculated_soil_z = :<7}) = '
        calcs[3] += f'({current_z = :<7}) + {direction} * ({distance = :.1f})'
        details = {'calcs': calcs, 'values': {
            'measured_distance': measured_distance,
            'z_offset': self.z_info['offset'],
            'new_meas_dist': measured_distance - self.z_info['offset'],
            'measured_at_z': measured_at_z,
            'measured_soil_z': measured_soil_z,
            'disparity_offset': disparity_offset,
            'calibration_factor': calibration_factor,
            'current_z': current_z,
            'direction': direction,
            'disparity': disparity_value,
            'disparity_delta': round(disparity_delta, 4),
            'calc_distance': round(distance, 4),
            'calculated_soil_z': calculated_soil_z,
        }}
        return calculated_soil_z, details

    def _combine_disparity(self, stereo):
        disparities = []
        for j, left_image in enumerate(self.input_images['left']):
            for k, right_image in enumerate(self.input_images['right']):
                left = left_image.preprocess()
                right = right_image.preprocess()
                result = stereo.compute(left, right)
                multiple = len(self.input_images['left']) > 1
                if self.settings['verbose'] > 5 and multiple:
                    disparity = self.init_img(result)
                    disparity.normalize()
                    disparity.save(f'depth_map_bw_{j}_{k}')
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
        self.output_images['disparity'] = self.init_img(
            disparity_data, {'tag': 'disparity'})
        self.output_images['disparity'].reduce_data()
        if self.output_images['disparity'].data.data.max() < 1:
            self.log.error('Zero disparity.')
        if self.settings['verbose'] > 1:
            self.save_output_images()
        return self.output_images['disparity'].data.report

    def save_output_images(self):
        'Save un-rotated depth maps and histograms according to verbosity setting.'
        images = self.output_images
        images['depth'] = self.init_img(images['disparity'].image)
        images['depth'].normalize()
        depth_data = images['disparity'].data
        soil_z, _ = self.calculate_soil_z(depth_data.reduced['stats']['mid'])
        z_prefix = f'{soil_z}_' if soil_z is not None else ''
        if self.settings['verbose'] > 5 or self.settings['verbose'] == 3:
            images['depth_bw'] = self.init_img(images['depth'].image)
            images['depth_bw'].rotate(-1)
            images['depth_bw'].add_soil_z_annotation(soil_z)
            images['depth_bw'].save(f'{z_prefix}depth_map_bw')
        if self.settings['verbose'] > 4 or self.settings['verbose'] == 2:
            left = self.input_images['left'][0]
            images['depth_color'] = self.init_img(images['depth'].image)
            images['depth_color'].colorize_depth(depth_data)
            images['depth_color'].rotate(-1)
            images['depth_blend'] = self.init_img(left.image)
            images['depth_blend'].blend_with(images['depth_color'].image)
        if self.settings['verbose'] > 4:
            left = self.input_images['left'][0]
            right = self.input_images['right'][0]
            for img in [left, right]:
                img.create_histogram(self.calculate_soil_z, simple=True)
            images['disparity'].create_histogram(self.calculate_soil_z)
            images['depth'].channel3()
            images['stereo_blend'] = self.init_img(left.image)
            images['stereo_blend'].blend_with(right.image)
            images['stereo_blend'].rotate()
            all_images = [
                [left.rotate_copy(),
                 right.rotate_copy(),
                 images['stereo_blend'].image],
                [images['depth'].image,
                 images['depth_color'].rotate_copy(),
                 images['depth_blend'].rotate_copy()],
                [left.histogram.histogram,
                 right.histogram.histogram,
                 images['disparity'].histogram.histogram]]
            collage = create_output_collage(all_images, soil_z)
            images['collage'] = self.init_img(collage)
            images['collage'].save('all')
            if self.settings['verbose'] > 5:
                images['depth_color'].save('disparity_map')
                images['disparity'].save_histogram('histogram')
                images['img_hists'] = self.init_img(left.histogram.histogram)
                images['img_hists'].blend_with(right.histogram.histogram)
                images['img_hists'].save('image_histogram_blend')
        if self.settings['verbose'] > 5 or self.settings['verbose'] == 2:
            images['depth_blend'].add_soil_z_annotation(soil_z)
            images['depth_blend'].save(f'{z_prefix}depth_map')

    def calculate(self):
        'Calculate disparity, calibration factor, and soil height.'
        self.check_images()

        missing_measured_distance = self.settings['measured_distance'] == 0
        missing_calibration_factor = self.settings['calibration_factor'] == 0
        if missing_measured_distance and missing_calibration_factor:
            self.log.error('Calibration measured distance input required.')

        disparity = self.calculate_disparity()
        self.log.debug(disparity['report'])
        disparity_log = f'Average disparity: {disparity["mid"]} '
        disparity_log += f'{disparity["coverage"]}% coverage'
        self.log.debug(disparity_log)
        if disparity['coverage'] < self.settings['disparity_coverage_threshold']:
            self.log.error('Not enough disparity information. Check images.')

        disparity_offset = self.settings['calibration_disparity_offset']
        missing_disparity_offset = disparity_offset == 0
        if missing_disparity_offset:
            print('Saving disparity offset...')
            self.settings['calibration_disparity_offset'] = disparity['mid']
            self.settings['calibration_measured_at_z'] = self.z_info['current']
            img_size = shape(self.input_images['left'][0].image)
            self.settings['calibration_image_width'] = img_size['width']
            self.settings['calibration_image_height'] = img_size['height']
        elif missing_calibration_factor:
            print('Calculating calibration factor...')
            disparity_difference = disparity['mid'] - disparity_offset
            if disparity_difference == 0:
                self.log.error('Zero disparity difference.')
            factor = round(self.z_info['offset'] / disparity_difference, 4)
            self.settings['calibration_factor'] = factor
            self.results.save_calibration()

        details = None
        if not missing_disparity_offset:
            soil_z, details = self.calculate_soil_z(disparity['mid'])
            self.log.debug('\n'.join(details['calcs']))
            if missing_calibration_factor:
                expected_soil_z = details['values']['measured_soil_z']
                if abs(soil_z - expected_soil_z) > 2:
                    error_message = 'Soil height calculation error: '
                    error_message += f'expected {expected_soil_z} got {soil_z}'
                    self.log.error(error_message)
            self.results.save_soil_height(soil_z)

            self.results.save_report(
                self.base_name, self.output_images, self.input_images, details)
        return details

#!/usr/bin/env python3.8

'Generate inputs from account images or upload point results.'

import os
import sys
import json
import getpass
import numpy as np
import requests
from tests import path


def get_input_value(key):
    'Get and store user input.'
    account_inputs_filename = path('account_inputs.json')
    prev = {}
    if os.path.exists(account_inputs_filename):
        with open(account_inputs_filename, 'r') as account_inputs_file:
            prev = json.load(account_inputs_file)
    prev['server'] = prev.get('server', 'https://my.farm.bot')
    prev_value = prev.get(key)
    prev_value_parens = f' ({prev_value})' if prev_value is not None else ''
    value = input(f'{key}{prev_value_parens}: ') or prev_value
    prev[key] = value
    with open(account_inputs_filename, 'w') as account_inputs_file:
        account_inputs_file.write(json.dumps(prev, indent=2))
    return value


def get_token():
    'Fetch account token.'
    if len(sys.argv) > 2:
        token_string = sys.argv[2]
        token_json = json.loads(token_string)
        iss = token_json['token']['unencoded']['iss']
        server_base, port = iss.split(':')
        server = f"http{'s' if port == 443 else ''}:{server_base}:{port}"
        token = token_json['token']['encoded']
    else:
        server = get_input_value('server')
        email = get_input_value('email')
        password = getpass.getpass('password: ')
        user = {'user': {'email': email, 'password': password}}
        url = f'{server}/api/tokens'
        token_headers = {'content-type': 'application/json'}
        response = requests.post(url, headers=token_headers, json=user)
        response.raise_for_status()
        token = response.json()['token']['encoded']
    api_headers = {'Authorization': f'Bearer {token}',
                   'content-type': 'application/json'}
    return server, api_headers


def get_image_records(server, headers):
    'Fetch image endpoint records.'
    response = requests.get(f'{server}/api/images', headers=headers)
    response.raise_for_status()
    images = response.json()
    return images


def check_image_match(img_a, img_b, offset=10):
    'Determine if image is part of a stereo pair.'
    def _match(loc_a, loc_b):
        return abs(loc_a - loc_b) < 1

    def _is_stereo(img):
        name = img['meta']['name']
        return 'left' in name or 'right' in name

    def _both_stereo():
        return _is_stereo(img_a) and _is_stereo(img_b)
    coord_a = img_a['meta']
    coord_b = img_b['meta']
    x_match = _match(coord_a['x'], coord_b['x'])
    y_match = _match(coord_a['y'], coord_b['y']) and _both_stereo()
    y_offset_f_match = _match(coord_a['y'], coord_b['y'] + offset)
    y_offset_r_match = _match(coord_a['y'], coord_b['y'] - offset)
    y_offset_match = y_offset_f_match or y_offset_r_match
    z_match = _match(coord_a['z'], coord_b['z'])
    return all([x_match, y_match or y_offset_match, z_match])


def generate_inputs():
    'Convert image endpoint records to inputs.'
    server, headers = get_token()
    inputs = {}
    measured_distance = float(get_input_value('measured distance'))
    inputs['settings'] = {
        'measured_distance': measured_distance,
        'calibration_factor': float(get_input_value('calibration factor')),
        'calibration_disparity_offset': float(get_input_value('disparity offset')),
    }
    inputs['images'] = []
    images = get_image_records(server, headers)
    for i, image in enumerate(images):
        if i == 0:
            continue
        prev_img = images[i - 1]
        if check_image_match(image, prev_img):
            matched = sorted([image, prev_img], key=lambda i: i['meta']['y'])
            inputs['images'].append([{
                'left': [{'url': matched[0]['attachment_url'],
                          'location': matched[0]['meta']}],
                'right': [{'url': matched[1]['attachment_url'],
                           'location': matched[1]['meta']}],
                'expected': -measured_distance}])
    device_id = images[-1]['device_id']
    server_label = server.split('//')[1][:2]
    data_path = path('data')
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    filename = f'{data_path}/{server_label}_device_{device_id}.json'
    with open(filename, 'w') as input_file:
        input_file.write(json.dumps(inputs, indent=2))


def load_points():
    'Load points from output file.'
    filename = get_input_value('points filename')
    with open(filename, 'r') as points_file:
        points = json.load(points_file)
    return np.hstack(points)


def upload_points():
    'Upload points to account.'
    points = load_points()
    server, headers = get_token()
    point_name = get_input_value('point name')
    color = get_input_value('point color')
    for point in points:
        new_point = {
            'name': point_name,
            'pointer_type': 'GenericPointer',
            'x': point['x'],
            'y': point['y'],
            'z': point['z'],
            'meta': {'color': color, 'at_soil_level': 'true'},
        }
        url = f'{server}/api/points'
        response = requests.post(url, headers=headers, json=new_point)
        response.raise_for_status()


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ['upload', 'download']:
        COMMAND = 'python -m tests.account'
        print('usage:')
        print(f'  download image inputs: `{COMMAND} download [token]`')
        print(f'   upload point results: `{COMMAND} upload [token]`')
    elif sys.argv[1] == 'download':
        generate_inputs()
    elif sys.argv[1] == 'upload':
        upload_points()

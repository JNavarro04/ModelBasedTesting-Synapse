import logging
import time
from datetime import datetime

import requests

from generic.api import label_pb2
from generic.api.configuration import ConfigurationItem, Configuration
from generic.api.label import Label, Sort
from generic.api.parameter import Type
from generic.handler import Handler as AbstractHandler

# Labels
CHANNEL = 'matrix'

STIMULI = {
    'admin_invite': ('admin', 'invite'),
    'admin_kick':   ('admin', 'kick'),
    'admin_ban':    ('admin', 'ban'),
    'admin_unban':  ('admin', 'unban'),
    'bob_join':     ('bob',   'join'),
    'bob_leave':    ('bob',   'leave'),
    'eve_kick':     ('eve',   'kick'),
    'eve_ban':      ('eve',   'ban'),
}

RESPONSES = {200: 'ok', 403: 'forbidden'}

#Connection handler
class Handler(AbstractHandler):

    def __init__(self):
        super().__init__()
        self.base_url = None
        self.users = {}
        self.room_id = None

    def supported_labels(self):
        stimuli = [Label(Sort.STIMULUS, name, CHANNEL) for name in STIMULI]
        responses = [Label(Sort.RESPONSE, name, CHANNEL) for name in RESPONSES.values()]
        return stimuli + responses

    def default_configuration(self):
        return Configuration([ConfigurationItem(
            name='synapse_url',
            tipe=Type.STRING,
            description='Base URL of the Synapse homeserver',
            value='http://localhost:8008')])

    # Talking functions
    def _call(self, method, path, user=None, body=None):
        headers = {'Authorization': f'Bearer {self.users[user]["token"]}'} if user else {}
        return requests.request(method, self.base_url + path, json=body or {}, headers=headers)

    def _register(self, username):
        r = self._call('POST', '/register', body={
            'username': username, 'password': 'pw',
            'auth': {'type': 'm.login.dummy'}})
        r.raise_for_status()
        return {'id': r.json()['user_id'], 'token': r.json()['access_token']}

    def _new_room(self):
        r = self._call('POST', '/createRoom', 'admin', {'preset': 'private_chat'})
        r.raise_for_status()
        self.room_id = r.json()['room_id']
        self._call('POST', f'/rooms/{self.room_id}/invite', 'admin', {'user_id': self.users['eve']['id']})
        self._call('POST', f'/rooms/{self.room_id}/join', 'eve')

    def _membership_request(self, actor, action):
        path = f'/rooms/{self.room_id}/{action}'
        if action in ('join', 'leave'):
            return self._call('POST', path, actor)
        return self._call('POST', path, actor, {'user_id': self.users['bob']['id']})
    
    def start(self):
        self.base_url = self.configuration.items[0].value + '/_matrix/client/v3'
        suffix = str(int(time.time()))
        for name in ('admin', 'bob', 'eve'):
            self.users[name] = self._register(name + suffix)
        self._new_room()
        self.adapter_core.send_ready()

    def reset(self):
        self._new_room()
        self.adapter_core.send_ready()

    def stop(self):
        self.room_id = None

    def stimulate(self, pb_label):
        label = Label.decode(pb_label)
        actor, action = STIMULI[label.name]

        pb_label.timestamp = time.time_ns()
        pb_label.physical_label = bytes(f'{actor} {action}', 'UTF-8')
        self.adapter_core.send_stimulus_confirmation(pb_label)

        r = self._membership_request(actor, action)
        if r.status_code not in RESPONSES:
            raise RuntimeError(f'unexpected HTTP {r.status_code}: {r.text}')

        self.adapter_core.send_response(Label(
            sort=Sort.RESPONSE, name=RESPONSES[r.status_code], channel=CHANNEL,
            physical_label=bytes(f'{r.status_code} {r.text}', 'UTF-8'),
            timestamp=datetime.now()))



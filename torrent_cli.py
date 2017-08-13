# -*- coding: utf-8 -*-
import os
import socket
import ssl
from collections import deque

# DelugeRPC: http://dev.deluge-torrent.org/wiki/Development/DelugeRPC
# "All messages are zlib compressed rencoded strings"
# https://github.com/aresch/rencode
import zlib
import rencode

method_list = [
    ('core.get_free_space', ),
    ('core.get_free_space', '/'),
    ('core.get_free_space', '1', '2'),
    ('daemon.login', 'username', 'password')
]


class CustomRPC(object):
    def __init__(self, host='127.0.0.1', port=58846):
        auth_file = os.path.expanduser(os.path.join('~', '.config', 'deluge', 'auth'))
        with open(auth_file) as f:
            auth = f.read()

        self.username, self.password = auth.split(':')[:2]
        self.host = host
        self.port = port

        self.request_id = 1
        self.connected = False

        self._socket = ssl.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self._socket.settimeout(10)

    def connect(self):
        try:
            self._socket.connect((self.host, self.port))
        except ssl.SSLError as e:
            print('UNSUPPORTED_PROTOCOL')
            raise

        self.call('daemon.login', self.username, self.password)
        self.connected = True

    def disconnect(self):
        if self.connected:
            self._socket.close()

    def call(self, method, *args, **kwargs):
        self.request_id += 1
        request = ((self.request_id, method, args, kwargs), )
        comp_request = zlib.compress(rencode.dumps(request))

        # send
        self._socket.send(comp_request)

        # recv
        data_queue = deque()
        while True:
            try:
                d = self._socket.recv(64)
                data_queue.append(d)
            except ssl.SSLError:
                raise

            try:
                data = zlib.decompress(b''.join(data_queue))
            except zlib.error:
                if not d:
                    raise
                continue
            break

        data = list(rencode.loads(data))
        msg_type = data.pop(0)
        request_id = data.pop(0)
        print('request_id = {}'.format(request_id))

        if msg_type == 2:
            exception_type, exception_msg, traceback = data[0]
            print(exception_type, exception_msg, traceback, sep=', ')
            raise Exception
        elif msg_type == 1:
            return data[0]

if __name__ == '__main__':
    pass

import asyncio
import json
import logging
import platform
import time

import aiohttp

from .websocket_consts import EventType, Opcode
from .models import Message, Channel

logger = logging.getLogger(__name__)


class Client:
    API_URL = 'https://discordapp.com/api'

    def __init__(self, token, name='Bot', activity_name=None):
        self.token = token
        self.name = name
        self.headers = {
            'Authorization': f'Bot {self.token}',
            'User-Agent': self.name,
        }
        self.activity_name = activity_name

        self.on_message = None
        self.user = None
        self.start_time = None
        self.last_seq = None

    async def run(self, on_message):
        self.on_message = on_message
        resp = await self.request('GET', '/gateway')
        socket_url = resp['url']
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f'{socket_url}?v=6&encoding=json') as ws:
                self.start_time = time.time()
                logger.info('Websocket connected')
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.CLOSE:
                        logger.error(f'Discord closed the connection: {msg.data}, {msg.extra}')
                        raise Exception(f'Websocket closed')
                    if msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f'Websocket error response: {msg.data}')
                        raise Exception(f'Websocket error')
                    elif msg.type == aiohttp.WSMsgType.TEXT:
                        await self.handle_message(ws, msg.data)
                    else:
                        logger.warning(f'Unhandled type: {msg.type}, {msg.data}')
        raise Exception('This should never happen')

    async def request(self, method, path, headers=None, json_data=None, expect_json=True):
        if headers is None:
            headers = self.headers
        logger.debug(f'{method} {path} {headers} {json_data}')
        async with aiohttp.request(method, f'{self.API_URL}{path}', headers=headers, json=json_data) as response:
            # TODO: Implement a way of ensuring rate limits
            response.raise_for_status()
            if expect_json:
                return await response.json()

    async def handle_message(self, ws, msg):
        msg = json.loads(msg)
        op = msg['op']
        if msg.get('s'):
            self.last_seq = msg['s']
        typ = msg.get('t')
        data = msg.get('d')
        logger.info(f'Received: {op} {typ}')
        if op == Opcode.HELLO:
            logger.info(data)
            reply = {
                'op': Opcode.IDENTIFY,
                'd': {
                    'token': self.token,
                    'properties': {
                        '$os': platform.platform(terse=1),
                    },
                    'compress': False,
                }
            }
            if self.activity_name:
                reply['d']['presence'] = {
                    'game': {
                        'name': self.activity_name,
                        'type': 0,
                    },
                    'status': 'online',
                    'since': None,
                    'afk': False,
                }
            await ws.send_json(reply)
            asyncio.create_task(self.heartbeat(ws, data['heartbeat_interval']))
        elif op == Opcode.HEARTBEAT_ACK:
            logger.info('Heartbeat-ack received')
        elif op == Opcode.DISPATCH:
            logger.debug('Handling dispatch')
            await self.handle_dispatch(typ, data)
        else:
            logger.info(f'Did not handle opcode with data: {data}')

    async def heartbeat(self, ws, interval_ms):
        interval_sec = interval_ms / 1000
        data = {'op': Opcode.HEARTBEAT}
        while True:
            await asyncio.sleep(interval_sec)
            data['d'] = self.last_seq
            logger.info(f'Sending heartbeat {self.last_seq}')
            await ws.send_json(data)

    async def handle_dispatch(self, typ, data):
        if typ == EventType.READY:
            self.user = data['user']
            logger.info(f'Self data: {self.user}')
        elif typ == EventType.MESSAGE_CREATE:
            if self.on_message:
                message = Message(**data)
                logger.debug('Calling on_message handler')
                # TODO: Replies to any single channel should not be out of order.
                asyncio.create_task(self.on_message(self, message))
        else:
            # nothing else supported
            pass

    async def send_message(self, message, channel_id):
        logger.info(f'Replying to channel {channel_id}')
        await self.request('POST', f'/channels/{channel_id}/messages', json_data=message)

    async def get_channel(self, channel_id):
        logger.info(f'Getting channel with id: {channel_id}')
        channel_d = await self.request('GET', f'/channels/{channel_id}')
        return Channel(**channel_d)

    async def get_dm_channel(self, user_id):
        logger.info(f'Getting DM channel for user: {user_id}')
        json_data = {'recipient_id': user_id}
        channel_d = await self.request('POST', '/users/@me/channels', json_data=json_data)
        return Channel(**channel_d)

    async def trigger_typing(self, channel_id):
        logger.info(f'Triggering typing on channel {channel_id}')
        return await self.request('POST', f'/channels/{channel_id}/typing', expect_json=False)

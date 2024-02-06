#!/usr/bin/env python

# Reguirements :
#	python >= 3.7.4
#	modules : aiohttp, pycryptodome
#
# Note : Script expects remote messages as single line json :
#   {"talker":{"c":"Callsign","t":1}} // Session started
#	{"talker":{"c":"Callsign","t":0}} // Session ended

import aiohttp
import asyncio
import base64
import datetime
import json
import logging
import os
import socket
import subprocess
import sys
import time
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

with open('config.json') as cfg_file:
    cfg = json.load(cfg_file)

RWS_ENDPOINT = cfg['RWS_ENDPOINT']
ZWS_ENDPOINT = cfg['ZWS_ENDPOINT']
ZC_USERNAME = cfg['ZC_USERNAME']
ZC_PASSWORD = cfg['ZC_PASSWORD']
ZC_CHANNEL = cfg['ZC_CHANNEL']
ZC_ISSUER = cfg['ZC_ISSUER']
ZM_CLIENTS_FILE = cfg['ZM_CLIENTS_FILE']
ZM_TALKER_FILE = cfg['ZM_TALKER_FILE']
ZM_WS_FILE = cfg['ZM_WS_FILE']
LOGFILE = cfg['LOGFILE']
RC_NAME = cfg['RC_NAME']
ZC_NAME = cfg['ZC_NAME']

LOGFORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(filename=LOGFILE, level=logging.INFO, format=LOGFORMAT)

retries = 0

def wtf(path, data, m='w', n=False):
	try:
		with open(path, m) as f:
			f.write(str(data))
			if n:
				f.write('\n')
			f.flush()
			os.fsync(f.fileno())
	except Exception as e:
		logging.error(e)

def create_token(issuer):
	# Adapted from https://github.com/aaknitt/zellostream
	with open('private.key', "rb") as f:
		key = RSA.import_key(f.read())
	header = {"typ": "JWT", "alg": "RS256"}
	payload = {"iss": issuer, "exp": round(time.time() + 60)}
	signer = pkcs1_15.new(key)
	json_header = json.dumps(header, separators=(",", ":"), cls=None).encode("utf-8")
	json_payload = json.dumps(payload, separators=(",", ":"), cls=None).encode("utf-8")
	h = SHA256.new(base64.standard_b64encode(json_header) + b"." + base64.standard_b64encode(json_payload))
	signature = signer.sign(h)
	token = base64.standard_b64encode(json_header) + b"." + base64.standard_b64encode(json_payload) + b"." + base64.standard_b64encode(signature)
	return token.decode("utf-8")

async def endpoint_check(endpoint):
	while True:
		try:
			async with aiohttp.ClientSession() as session:
				async with session.ws_connect(endpoint) as ws:
					logging.info(f'Connection to {endpoint} succeeded')
					return
		except (NameError, aiohttp.client_exceptions.ClientError, IOError) as error:
			logging.error(error)
			await session.close()
			time.sleep(6)

async def authenticate(zws, ZC_USERNAME, ZC_PASSWORD, ZC_CHANNEL):
	global retries, ZC_ISSUER
	token = create_token(ZC_ISSUER)
	await zws.send_str(json.dumps({
		"command": "logon",
		"seq": 1,
		"auth_token": token,
		"username": ZC_USERNAME,
		"password": ZC_PASSWORD,
		"channel": ZC_CHANNEL
	}))

	is_authorized = False
	is_channel_available = False
	async for msg in zws:
		if msg.type == aiohttp.WSMsgType.TEXT:
			data = json.loads(msg.data)
			if "refresh_token" in data:
				is_authorized = True
				ZC_TOKEN = data["refresh_token"]
			elif "command" in data and "status" in data and data["command"] == "on_channel_status":
				is_channel_available = data["status"] == "online"
			if is_authorized and is_channel_available:
				break

	if not is_authorized or not is_channel_available:
		logging.error('Authentication failed or channel offline')
		retries += 1
		time.sleep(6)
		if retries > 5:
			logging.error('Too many retries. Restarting in 30 seconds')
			tasks = asyncio.all_tasks()
			await asyncio.gather(*(task.cancel() for task in tasks))
			time.sleep(30)
			sys.exit(0)

async def data_bridge(ZC_USERNAME, ZC_PASSWORD, ZC_CHANNEL):
	global RC_NAME, ZC_NAME
	last_push_ts = 0
	print(f'Zello Monitor has been started. Logging messages to {LOGFILE}')
	try:
		conn = aiohttp.TCPConnector(family = socket.AF_INET, ssl = False)
		async with aiohttp.ClientSession(connector = conn) as session:
			async with session.ws_connect(ZWS_ENDPOINT) as zws:
				await asyncio.wait_for(authenticate(zws, ZC_USERNAME, ZC_PASSWORD, ZC_CHANNEL), 6)
				logging.info(f'User [{ZC_USERNAME}] has been authenticated on channel [{ZC_CHANNEL}]')
				async for msg in zws:
					if msg.type == aiohttp.WSMsgType.TEXT:
						data = json.loads(msg.data)
						if "command" in data and "error" in data:
								msg_error = data["error"]
								logging.error(f'Error received from Zello server: {msg_error}')
						if "command" in data and "status" in data:
							if data["command"] == "on_channel_status":
								user_count = data["users_online"]
								wsdata = {'zello': {'command': 'on_channel_status', 'users_online': user_count}}
								wtf(ZM_WS_FILE, json.dumps(wsdata), n=True)
								wtf(ZM_CLIENTS_FILE, user_count)
								logging.info(f'Online users update received ({user_count})')
						if "command" in data and "from" in data:
							if data["command"] == "on_stream_start" and data["from"] != ZC_NAME:
								current_talker = data["from"]
								wsdata = {'zello': {'command': 'on_stream_start', 'from': current_talker}}
								wtf(ZM_WS_FILE, json.dumps(wsdata), n=True)
								wtf(ZM_TALKER_FILE, data["from"].strip().upper())
								logging.info(f'Voice session received from Zello talker ({current_talker})')
						if "command" in data and "from" in data:
							if data["command"] == "on_stream_start" and data["from"] == ZC_NAME and RWS_ENDPOINT != "svxlink":
								session = aiohttp.ClientSession()
								async with session.ws_connect(RWS_ENDPOINT) as rws:
									async for msg in rws:
										if msg.type == aiohttp.WSMsgType.TEXT:
											data = json.loads(msg.data)
											if "talker" in data:
												if data["talker"]["t"] == 0:
													await session.close()
													break
												if data["talker"]["c"] != RC_NAME:
													now = int(time.time())
													current_talker = data["talker"]["c"]
													if now - last_push_ts >= 6:
														logging.info(f'Voice session received from RoLink talker ({current_talker})')
														msg_txt = 'În emisie: ' + current_talker
														await zws.send_str(json.dumps({
															"command": "send_text_message",
															"seq": 3,
															"channel": ZC_CHANNEL,
															"text": msg_txt
														}))
														last_push_ts = now
													await session.close()
													break
						else:
							#do stuff from svxlink
							pass #for now
	except asyncio.TimeoutError:
		logging.warning('Communication timeout')
		time.sleep(12)

async def main():
    while True:
        try:
            logging.info('Zello Monitor has started')
            tasks = asyncio.gather(
                endpoint_check(RWS_ENDPOINT),
                endpoint_check(ZWS_ENDPOINT),
                data_bridge(ZC_USERNAME, ZC_PASSWORD, ZC_CHANNEL)
            )
            await tasks
            for task in tasks._children:
                if task.exception() is not None:
                    logging.error(f"Exception occurred: {task.exception()}")
        except aiohttp.ClientError as e:
            logging.error(e)
            time.sleep(6)
        except KeyboardInterrupt:
            sys.exit(0)

asyncio.run(main())

import os
import asyncio
import base64
import json
import time
import datetime
import aiohttp
import socket
import configparser

RWS_ENDPOINT = "wss://RoLink.network/wssx/"
ZWS_ENDPOINT = "wss://zello.io/ws"
ZWS_TIMEOUT_SEC = 2

def main():
    try:
        config = configparser.ConfigParser()
        config.read('helper.conf')
        username = config['zello']['username']
        password = config['zello']['password']
        token = config['zello']['token']
        channel = config['zello']['channel']
    except KeyError as error:
        print("Check config file. Missing key:", error)
        return

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(help_channel(username, password, token, channel))
    except KeyboardInterrupt:
        def shutdown_exception_handler(loop, context):
            if "exception" in context and isinstance(context["exception"], asyncio.CancelledError):
                return
            loop.default_exception_handler(context)

        loop.set_exception_handler(shutdown_exception_handler)
        tasks = asyncio.gather(*asyncio.all_tasks(loop=loop), return_exceptions=True)
        tasks.add_done_callback(lambda t: loop.stop())
        tasks.cancel()
        while not tasks.done() and not loop.is_closed():
            loop.run_forever()
        print("Stopped by user")
    finally:
        loop.close()



async def authenticate(zws, username, password, token, channel):
    await zws.send_str(json.dumps({
        "command": "logon",
        "seq": 1,
        "auth_token": token,
        "username": username,
        "password": password,
        "channel": channel
    }))

    is_authorized = False
    is_channel_available = False
    async for msg in zws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            data = json.loads(msg.data)
            if "refresh_token" in data:
                is_authorized = True
            elif "command" in data and "status" in data and data["command"] == "on_channel_status":
                is_channel_available = data["status"] == "online"
            if is_authorized and is_channel_available:
                break

    if not is_authorized or not is_channel_available:
        raise NameError('Authentication failed')

async def help_channel(username, password, token, channel):
    global ZelloWS
    last_talker=None
    try:
        conn = aiohttp.TCPConnector(family = socket.AF_INET, ssl = False)
        async with aiohttp.ClientSession(connector = conn) as session:
            async with session.ws_connect(ZWS_ENDPOINT) as zws:
                ZelloWS = zws
                await asyncio.wait_for(authenticate(zws, username, password, token, channel), ZWS_TIMEOUT_SEC)
                print(f"User {username} has been authenticated on {channel} channel")
                async for msg in zws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if "command" in data and "from" in data:
                            if data["command"] == "on_stream_start" and data["from"] == "RoLink GW":
                                session = aiohttp.ClientSession()
                                async with session.ws_connect(RWS_ENDPOINT) as rws:
                                    async for msg in rws:
                                        if msg.type == aiohttp.WSMsgType.TEXT:
                                            data = json.loads(msg.data)
                                            if "talker" in data:
                                                current_talker=data["talker"]["c"]
                                                if current_talker!=last_talker:
                                                    msg_txt = "Vorbeste: "+current_talker
                                                    log_txt = msg_txt + " @ " + datetime.datetime.now()
                                                    print(log_txt)
                                                    await zws.send_str(json.dumps({
                                                        "command": "send_text_message",
                                                        "seq": 3,
                                                        "channel": channel,
                                                        "text": msg_txt
                                                    }))
                                                    await session.close()
                                                    last_talker = current_talker
                                                    break
    except (NameError, aiohttp.client_exceptions.ClientError, IOError) as error:
        print(error)
    except asyncio.TimeoutError:
        print("Communication timeout")

if __name__ == "__main__":
    main()

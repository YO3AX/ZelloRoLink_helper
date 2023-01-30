#!/usr/bin/env python
import asyncio
from websockets import connect
import json

async def interogare_rolink(uri):
    async with connect(uri) as websocket:
        response = await websocket.recv()
        print (f"response = {response}")
        rolink = json.loads(response)
        caller=rolink["talker"]["c"]
        transmitting=rolink["talker"]["t"]
        talkgroup=rolink["talker"]["g"]
        r=rolink["talker"]["r"]
        duration=rolink["talker"]["s"]
        print(f"caller:{caller}")
        print(f"transmitting:{transmitting}")
        print(f"talkgroup:{talkgroup}")
        print(f"r:{r}")
        print(f"duration:{duration}")
asyncio.run(interogare_rolink("wss://svx.439100.ro/wssx/"))

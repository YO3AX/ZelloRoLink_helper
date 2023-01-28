import asyncio
import aiohttp
import json

async def main():
    session = aiohttp.ClientSession()
    async with session.ws_connect('wss://svx.439100.ro/wssx/') as ws:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                print(data)
                if "talker" in data:
                    caller=data["talker"]["c"]
                    print(caller)
                    await session.close()
                    break
            if msg.type in (aiohttp.WSMsgType.CLOSED,
                            aiohttp.WSMsgType.ERROR):
                print("error")
                break
if __name__ == '__main__':
#    print('Type "exit" to quit')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

# Zello-Monitor (helper)

This tool was custom-made for the RoLink network and serves as an example of how to enhance the user experience of the crosslinked RoLink.network and Zello channel (https://zello.com/ZelloRoLink). It demonstrates how to send bi-directional information, including the current talker, between the Zello Channel and the RoLink reflector.

Prerequisites :
Python >= 3.7.4
Python modules : aiohttp, pycryptodome
Assuming you already have a Zello Channel crosslinked with a SVXLink reflector,
go to https://github.com/zelloptt/zello-channel-api/blob/master/AUTH.md and follow the steps to get your issuer and keys

Note on Python version requirement :
https://github.com/aio-libs/aiohttp/issues/3535#issuecomment-483268542

How to install (Debian 10/11) :
1. Copy zello-monitor.py, config.json and private.key files to /opt/zello-monitor/
2. Copy zello-monitor.service to /lib/systemd/system/
3. Edit the file /opt/zello-monitor/private.key and fill the private key
4. Edit the file /opt/zello-monitorconfig.json and change the variables
5. Execute the command $systemctl daemon-reload && systemctl enable zello-monitor && systemctl start zello-monitor
6. Check the log file (/var/log/zello-monitor.log) for messages

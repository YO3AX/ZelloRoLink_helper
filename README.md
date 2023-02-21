# ZelloRoLink_helper

This code is supposed to help enhance the RoLink.network crosslinked Zello channel (https://zello.com/ZelloRoLink) experience by sending text information regarding the currently talking svxlink node / repeater.

The code works, but still needs to be enhanced.
To Do:
1) make the script run in autonomy even if Zello connection is lost (e.g. temporary network failure).
1.1. automatic re-login in case of log off or stale connection.
2) make the script auto start inside the crosslink VM
3) put a wathdog to monitor the script and restart it in case of failure.

"""Offline guard for run_all_checks.sh: deny all IP network access in every Python process started with this
directory on PYTHONPATH (child processes inherit it). Uses an audit hook, which cannot be removed once installed.
Local AF_UNIX sockets and pipes (used by multiprocessing) stay allowed."""

import socket
import sys

_IP = {socket.AF_INET, getattr(socket, "AF_INET6", socket.AF_INET)}


class NetworkBlocked(RuntimeError):
    pass


def _hook(event, args):
    if event in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"):
        raise NetworkBlocked(f"offline guard: {event} denied")
    if event in ("socket.connect", "socket.sendto", "socket.sendmsg"):
        sock = args[0]
        if getattr(sock, "family", None) in _IP:
            raise NetworkBlocked(f"offline guard: {event} denied")


sys.addaudithook(_hook)

GUARD_INSTALLED = True

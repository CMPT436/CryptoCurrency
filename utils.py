import binascii
import time
import json
import hashlib
import threading
import logging
import socketserver
import socket
import random
import os
from functools import lru_cache, wraps
from typing import (
    Iterable, NamedTuple, Dict, Mapping, Union, get_type_hints, Tuple,
    Callable)

import ecdsa
from base58 import b58encode_check

#get dict of peers from enviroment
peer_hostnames = {p for p in os.environ.get('TC_PEERS', '').split(',') if p}

# Signal when the initial block download has completed.
ibd_done = threading.Event()

class GetBlocksMsg(NamedTuple):  # Request blocks during initial sync
    pass
class InvMsg(NamedTuple):  # Convey blocks to a peer who is doing initial sync
    pass
class GetUTXOsMsg(NamedTuple):  # List all UTXOs
    pass
class GetMempoolMsg(NamedTuple):  # List the mempool
    pass
class GetActiveChainMsg(NamedTuple):  # Get the active chain in its entirety.
    pass
class AddPeerMsg(NamedTuple):
    pass
def read_all_from_socket(req) -> object:
    pass

def send_to_peer(data, peer=None):
    pass

def int_to_8bytes(a: int) -> bytes: return binascii.unhexlify(f"{a:0{8}x}")
    pass

def encode_socket_data(data: object) -> bytes:
    pass

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass
class TCPHandler(socketserver.BaseRequestHandler):
    pass

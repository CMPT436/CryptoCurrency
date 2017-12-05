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
import validation
from base58 import b58encode_check

################################### Transactions ###############################
# Used to represent the specific output within a transaction.
OutPoint = NamedTuple('OutPoint', [('txid', str), ('txout_idx', int)])


class TxIn(NamedTuple):
    """Inputs to a Transaction."""
    # A reference to the output we're spending. This is None for coinbase
    # transactions.
    to_spend: Union[OutPoint, None]

    # The (signature, pubkey) pair which unlocks the TxOut for spending.
    unlock_sig: bytes
    unlock_pk: bytes

    # A sender-defined sequence number which allows us replacement of the txn
    # if desired.
    sequence: int


class TxOut(NamedTuple):
    """Outputs from a Transaction."""
    # The number of Ralphies this awards.
    value: int

    # The public key of the owner of this transaction
    to_address: str


class UnspentTxOut(NamedTuple):
    value: int
    to_address: str

    # The ID of the transaction this output belongs to.
    txid: str
    txout_idx: int

    # Did this TxOut from from a coinbase transaction?
    is_coinbase: bool

    # The blockchain height this TxOut was included in the chain.
    height: int

    @property
    def outpoint(self):
        return OutPoint(self.txid, self.txout_idx)


class Transaction(NamedTuple):
    txins: Iterable[TxIn]
    txouts: Iterable[TxOut]

    # The block number or timestamp at which this transaction is unlocked.
    # < 500000000: Block number at which this transaction is unlocked.
    # >= 500000000: UNIX timestamp at which this transaction is unlocked.
    locktime: int = None

    @property
    def is_coinbase(self) -> bool:
        return ( len(self.txins) == 1 ) and ( self.txins[0].to_spend is None )

    @classmethod
    def create_coinbase(cls, pay_to_addr, value, height):
        return cls(
            txins=[TxIn(
                to_spend=None,
                # Push current block height into unlock_sig so that this
                # transaction's ID is unique relative to other coinbase txns.
                unlock_sig=str(height).encode(),
                unlock_pk=None,
                sequence=0)],
            txouts=[TxOut(
                value=value,
                to_address=pay_to_addr)],
        )

    @property
    def id(self) -> str:
        return sha256d(serialize(self))

    def validate_basics(self, as_coinbase=False):
        if (not self.txouts) or (not self.txins and not as_coinbase):
            raise TxnValidationError('Missing txouts or txins')

        if len(serialize(self)) > Params.MAX_BLOCK_SERIALIZED_SIZE:
            raise TxnValidationError('Too large')

        if sum(t.value for t in self.txouts) > Params.MAX_MONEY:
            raise TxnValidationError('Spend value too high')
#################################### Mempool ###################################
# dictionary of unmined transactions.
mempool: Dict[str, Transaction] = {}

# Set of orphaned (i.e. has inputs referencing yet non-existent UTXOs)
# transactions.
orphan_txns: Iterable[Transaction] = []


def find_utxo_in_mempool(txin) -> UnspentTxOut:
    #get txin id and txout id
    txid, idx = txin.to_spend

    #check mempool for transactionOut
    try:
        txout = mempool[txid].txouts[idx]
    except Exception: #if it isn't in the mempool return none
        logger.debug("Couldn't find utxo in mempool for %s", txin)
        return None
    #returns unspent out transaction
    return UnspentTxOut(
        *txout, txid=txid, is_coinbase=False, height=-1, txout_idx=idx)

#takes an empty block and fills it with transactions from mempool
def select_from_mempool(block: Block) -> Block:

    #a set is a unorganised collection of unique items
    added_to_block = set()

    #checks if block size is less then max
    def check_block_size(b) -> bool:
        return len(serialize(block)) < Params.MAX_BLOCK_SERIALIZED_SIZE

    # tries to add a transaction to a block
    def try_add_to_block(block, txid) -> Block:

        #if transaction is already in block we're done
        if txid in added_to_block:
            return block

        #gets transaction from mempool
        tx = mempool[txid]

        # For any txin that can't be found in the main chain, find its
        # transaction in the mempool (if it exists) and add it to the block.
        for txin in tx.txins:
            if txin.to_spend in utxo_set:
                continue

            in_mempool = find_utxo_in_mempool(txin)

            if not in_mempool:
                logger.debug(f"Couldn't find UTXO for {txin}")
                return None

            block = try_add_to_block(block, in_mempool.txid)
            if not block:
                logger.debug(f"Couldn't add parent")
                return None

        #creates a "new" block with the new transaction added
        newblock = block._replace(txns=[*block.txns, tx])
        #if newblock isnt to big we got a new block else we're stuck with the old one
        if check_block_size(newblock):
            logger.debug(f'added tx {tx.id} to block')
            added_to_block.add(txid)
            return newblock
        else:
            return block

    #for every transaction in the mempool try and add it to the block
    for txid in mempool:
        #our new block with the transaction added
        newblock = try_add_to_block(block, txid)
        #if the newblock is still in the size range we keep on adding
        if check_block_size(newblock):
            block = newblock
        else: # else we return the block
            break

    return block

#add a transaction to the mempool
def add_txn_to_mempool(txn: Transaction):
    # if transaction is already in the mempool we're done
    if txn.id in mempool:
        logger.info(f'txn {txn.id} already seen')
        return
    #validate transaction
    try:
        txn = validate_txn(txn)
    except TxnValidationError as e:
        if e.to_orphan:
            logger.info(f'txn {e.to_orphan.id} submitted as orphan')
            orphan_txns.append(e.to_orphan)
        else:
            logger.exception(f'txn rejected')
    else:
        #if the transaction is good add it to mempool
        logger.info(f'txn {txn.id} added to mempool')
        mempool[txn.id] = txn
        #and send the transaction to others
        for peer in peer_hostnames:
            send_to_peer(txn, peer)
#################################### Utils #####################################
# Peer-to-peer

#get dict of peers from enviroment
peer_hostnames = {p for p in os.environ.get('TC_PEERS', '').split(',') if p}

# Signal when the initial block download has completed.
ibd_done = threading.Event()

class GetBlocksMsg(NamedTuple):  # Request blocks during initial sync
    from_blockid: str
    CHUNK_SIZE = 50

    def handle(self, sock, peer_hostname):
        logger.debug(f"[p2p] recv getblocks from {peer_hostname}")

        _, height, _ = locate_block(self.from_blockid, active_chain)

        # If we don't recognize the requested hash as part of the active
        # chain, start at the genesis block.
        if(height is none):
            height = 1
        with chain_lock:
            blocks = active_chain[height:(height + self.CHUNK_SIZE)]

        logger.debug(f"[p2p] sending {len(blocks)} to {peer_hostname}")

    send_to_peer(InvMsg(blocks), peer_hostname)

class InvMsg(NamedTuple):  # Convey blocks to a peer who is doing initial sync
    blocks: Iterable[str]

    def handle(self, sock, peer_hostname):
        logger.info(f"[p2p] recv inv from {peer_hostname}")

        new_blocks = [b for b in self.blocks if not locate_block(b.id)[0]]

        if not new_blocks:
            logger.info('[p2p] initial block download complete')
            ibd_done.set()
            return

        for block in new_blocks:
            connect_block(block)

        new_tip_id = active_chain[-1].id
        logger.info(f'[p2p] continuing initial block download at {new_tip_id}')

        with chain_lock:
            # "Recursive" call to continue the initial block sync.
            send_to_peer(GetBlocksMsg(new_tip_id))

class GetUTXOsMsg(NamedTuple):  # List all UTXOs
    def handle(self, sock, peer_hostname):
        sock.sendall(encode_socket_data(list(utxo_set.items())))


class GetMempoolMsg(NamedTuple):  # List the mempool
    def handle(self, sock, peer_hostname):
        sock.sendall(encode_socket_data(list(mempool.keys())))


class GetActiveChainMsg(NamedTuple):  # Get the active chain in its entirety.
    def handle(self, sock, peer_hostname):
        sock.sendall(encode_socket_data(list(active_chain)))


class AddPeerMsg(NamedTuple):
    peer_hostname: str

    def handle(self, sock, peer_hostname):
        peer_hostnames.add(self.peer_hostname)


def read_all_from_socket(req) -> object:
    data = b''
    # Our protocol is: first 4 bytes signify msg length.
    msg_len = int(binascii.hexlify(req.recv(4) or b'\x00'), 16)

    while msg_len > 0:
        tdat = req.recv(1024)
        data += tdat
        msg_len -= len(tdat)

    return deserialize(data.decode()) if data else None


def send_to_peer(data, peer=None):
    """Send a message to a (by default) random peer."""
    global peer_hostnames

    peer = peer or random.choice(list(peer_hostnames))
    tries_left = 3

    while tries_left > 0:
        try:
            with socket.create_connection((peer, PORT), timeout=1) as s:
                s.sendall(encode_socket_data(data))
        except Exception:
            logger.exception(f'failed to send to peer {peer}')
            tries_left -= 1
            time.sleep(2)
        else:
            return

    logger.info(f"[p2p] removing dead peer {peer}")
    peer_hostnames = {x for x in peer_hostnames if x != peer}


def int_to_8bytes(a: int) -> bytes: return binascii.unhexlify(f"{a:0{8}x}")


def encode_socket_data(data: object) -> bytes:
    """Our protocol is: first 4 bytes signify msg length."""
    to_send = serialize(data).encode()
    return int_to_8bytes(len(to_send)) + to_send


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class TCPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        data = read_all_from_socket(self.request)
        peer_hostname = self.request.getpeername()[0]
        peer_hostnames.add(peer_hostname)

        if hasattr(data, 'handle') and isinstance(data.handle, Callable):
            logger.info(f'received msg {data} from peer {peer_hostname}')
            data.handle(self.request, peer_hostname)
        elif isinstance(data, Transaction):
            logger.info(f"received txn {data.id} from peer {peer_hostname}")
            add_txn_to_mempool(data)
        elif isinstance(data, Block):
            logger.info(f"received block {data.id} from peer {peer_hostname}")
            connect_block(data)

#exceptions
class BaseException(Exception):
    def __init__(self, msg):
        self.msg = msg

class TxUnlockError(BaseException):
    pass

class TxnValidationError(BaseException):
    def __init__(self, *args, to_orphan: Transaction = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.to_orphan = to_orphan

class BlockValidationError(BaseException):
    def __init__(self, *args, to_orphan: Block = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.to_orphan = to_orphan


def serialize(obj) -> str:
    pass

def deserialize(serialized: str) -> object:
    pass

def sha256d(s: Union[str, bytes]) -> str:
    """A double SHA-256 hash."""
    if not isinstance(s, bytes):
        s = s.encode()

    return hashlib.sha256(hashlib.sha256(s).digest()).hexdigest()

#TODO move this somewhere else
def chunks(l, n) -> Iterable[Iterable]:
    pass
#################################### Main ######################################

#get port variable from enviroment
PORT = os.environ.get('TC_PORT', 9999)

def main():
    #gets saved chain or we'll get a new one
    load_from_disk()

    #initializes the server and workers
    workers = []
    server = ThreadedTCPServer(('0.0.0.0', PORT), TCPHandler)


    def start_worker(fnc):
        workers.append(threading.Thread(target=fnc, daemon=True))
        workers[-1].start()


    logger.info(f'[p2p] listening on {PORT}')
    #start server worker
    start_worker(server.serve_forever)

    if peer_hostnames:
        logger.info(
            f'start initial block download from {len(peer_hostnames)} peers')
        send_to_peer(GetBlocksMsg(active_chain[-1].id))
        ibd_done.wait(60.)  # Wait a maximum of 60 seconds for IBD to complete.

    #start mining worker
    start_worker(mine_forever)
    #this makes main run until both workers dies
    [w.join() for w in workers]


if __name__ == '__main__':
    signing_key, verifying_key, my_address = init_wallet()
main()

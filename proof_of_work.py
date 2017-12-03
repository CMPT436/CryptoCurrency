"""
Proof of Work

POW is a way to improve cryptocurrency's secureness

work must be invested to add a block to the blockchain 
so that it is easier to add a block than to try to 
modify previous blocks in the chain

this is done by putting restrictions on the hash codes 
created from the transactions

rewards are given to users who solve these problems 
for incentive to mine the blocks


""" 
import time
import json
import threading


class Params:

	#the number of right bitshifts on 2^256 
	#to initialize the difficulty of mining
	INITIAL_DIFFICULTY_BITS = 24

	#the desired time(seconds) elapsed between blocks being mined
	DESIRED_SECONDS_BETWEEN_BLOCKS = 60

	# period of time for a difficulty target to be in place
	DIFFICULTY_PERIOD = (60 * 60 * 10)

	# re-calculate difficulty after DIFFICULTY_PERIOD_IN_BLOCKS are mined
	DIFFICULTY_PERIOD_IN_BLOCKS = (DIFFICULTY_PERIOD / DESIRED_SECONDS_BETWEEN_BLOCKS)


	# cut mining subsidy in half after this many blocks
	CUT_SUBSIDY_AFTER_THIS_MANY_BLOCKS = 210_000

	COIN_VALUE = 100_000_000


def get_difficulty_of_problem(prev_block_hash: str) -> int:
	"""
	get the difficulty that must be solved for the next block
	"""

	if prev_block_hash == "":
		return Params.INITIAL_DIFFICULTY_BITS


	(prev_block, prev_height, prev_chain_idx) = locate_block(prev_block_hash)

	with chain_lock:
		if prev_height - Params.DIFFICULTY_PERIOD_IN_BLOCKS > 0:
			this_block = active_chain[prev_height - Params.DIFFICULTY_PERIOD_IN_BLOCKS]
		else:
			this_block = active_chain[0]


	prev_block_time_solve = prev_block.timestamp - this_block.timestamp

	# if it took less time than targeted, increase difficulty
	if prev_block_time_to_solve < Params.DIFFICULTY_PERIOD:
		return prev_block.bits + 1
	else: #increase difficulty
		return prev_block.bits - 1

def construct_block(pay_to_addr, txns=None):
	"""

	"""
	with chain_lock:
		if active_chain:
			prev_block_hash = active_chain[-1].id
		else:
			prev_block_hash = None

	block = Block(
        version=0,
        prev_block_hash=prev_block_hash,
        merkle_hash='',
        timestamp=int(time.time()),
        bits=get_difficulty_of_problem(prev_block_hash),
        nonce=0,
        txns=txns or [],
    )

    if not block.txns:
    	block = select_from_mempool(block)

    # calculate and add miner's reward to block
    fees = calculate_fees(block)

    my_address = init_wallet()[2]

    coinbase_txn = Transaction.create_coinbase(
        my_address, (get_block_subsidy() + fees), len(active_chain))

    block = block._replace(txns=[coinbase_txn, *block.txns])
    block = block._replace(merkle_hash=get_merkle_root_of_txns(block.txns).val)

    if len(serialize(block)) > Params.MAX_BLOCK_SERIALIZED_SIZE:
        raise ValueError('txns specified create a block too large')

    return mine(block)


def calculate_fees(block) -> int:
	#the reward given to the miner

	fee = 0
	spent = 0
	sent = 0



	def utxo_from_block(txin):
        tx = [t.txouts for t in block.txns if t.id == txin.to_spend.txid]
        return tx[0][txin.to_spend.txout_idx] if tx else None

    def find_utxo(txin):
        return utxo_set.get(txin.to_spend) or utxo_from_block(txin)

    for txn in block.txns:
        spent = sum(find_utxo(i).value for i in txn.txins)
        sent = sum(o.value for o in txn.txouts)
        fee += (spent - sent)

	return fee



def get_block_subsidy() -> int:
	# more rewards to miner

	if len(active_chain) // Params.CUT_SUBSIDY_AFTER_THIS_MANY_BLOCKS > 63:
		return 0
	else:
		return Params.COIN_VALUE // 2**(len(active_chain) // Params.CUT_SUBSIDY_AFTER_THIS_MANY_BLOCKS)


stop_mining = threading.Event()

def mine(block):
	start_time = time.time()
	nonce = 0
	difficulty_target = (1<<(256 - block.bits))
	stop_mining.clear()

	while sha256(block.header(nonce)) > target:
		nonce = nonce + 1
		if nonce % 10000 == 0 and stop_mining.is_set():
			stop_mining.clear()
			return None

	block = block._replace(nonce=nonce)
	time_elapsed = time.time() - start or 0.01

	return block


def mine_forever():
	addr = init_wallet()[2]
	while True:
		block = construct_block(addr)

		if block:
			connect_block(block)
			save_to_disk()

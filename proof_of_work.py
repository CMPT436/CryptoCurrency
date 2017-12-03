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


def get_difficulty_of_problem(prev_block_hash: str) -> int:
	"""
	get the difficulty that must be solved for the next block
	"""

	if prev_block_hash = "":
		return Params.INITIAL_DIFFICULTY_BITS


	(prev_block, prev_height, prev_chain_idx) = locate_block(prev_block_hash)

	with chain_lock:
		if prev_height - Params.DIFFICULTY_PERIOD_IN_BLOCKS > 0:
			this_block = active_chain[prev_height - Params.DIFFICULTY_PERIOD_IN_BLOCKS]
		else:
			this_block = active_chain[0]


	prev_block_time_taken_to_solve = prev_block.timestamp - this_block.timestamp

	# if it took less time than targeted, increase difficulty
	if prev_block_time_taken_to_solve < Params.DIFFICULTY_PERIOD_IN_SECS_TARGET
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

"""
def calculate_fees(block) -> int:
	#the reward given to the miner

	fee = 0
	spent = 0
	sent = 0

	for txn in block.txns:
		spent = 

	fee = spent - sent
	return fee



def get_block_subsidy() -> int:


def mine(block):


def mine_forever():
"""
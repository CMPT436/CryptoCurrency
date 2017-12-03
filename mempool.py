# dictionary of unmined transactions.
mempool: dict[str, Transaction] = {}

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

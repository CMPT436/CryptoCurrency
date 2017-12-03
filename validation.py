import SERCcoin.py

def validate_txn(txn: Transaction,
                 as_coinbase: bool = False,
                 siblings_in_block: Iterable[Transaction] = None,
                 allow_utxo_from_mempool: bool = True,
                 ) -> Transaction:
    """
    Validate a single transaction. Used in various contexts, so the
    parameters facilitate different uses.
    """
    txn.validate_basics(as_coinbase=as_coinbase)

    available_to_spend = 0

    #using enumerate for better exceptions messages
    for i, txin in enumerate(txn.txins):

        utxo = utxo_set.get(txin.to_spend)

        if siblings_in_block:
            if utxo is None:
                utxo = find_utxo_in_list(txin, siblings_in_block)

        if allow_utxo_from_mempool:
            if utxo is None:
                utxo = find_utxo_in_mempool(txin)

        if not utxo:
            raise TxnValidationError(
                f'Could find no UTXO for TxIn[{i}] -- orphaning txn',
                to_orphan=txn)

        if utxo.is_coinbase and \
                (get_current_height() - utxo.height) < Params.COINBASE_MATURITY:
            raise TxnValidationError(f'Coinbase UTXO not ready for spend')

        try:
            validate_signature_for_spend(txin, utxo, txn)
        except TxUnlockError:
            raise TxnValidationError(f'{txin} is not a valid spend of {utxo}')

        available_to_spend += utxo.value


    if available_to_spend < sum(o.value for o in txn.txouts):
        raise TxnValidationError('Spend value is more than available')

    return txn


def validate_signature_for_spend(txin, utxo: UnspentTxOut, txn):
    pubkey_as_addr = pubkey_to_address(txin.unlock_pk)
    verifying_key = ecdsa.VerifyingKey.from_string(
        txin.unlock_pk, curve=ecdsa.SECP256k1)

    if pubkey_as_addr != utxo.to_address:
        raise TxUnlockError("Pubkey doesn't match")

    try:
        spend_msg = build_spend_message(
            txin.to_spend, txin.unlock_pk, txin.sequence, txn.txouts)
        verifying_key.verify(txin.unlock_sig, spend_msg)
    except Exception:
        logger.exception('Key verification failed')
        raise TxUnlockError("Signature doesn't match")

    return True


def build_spend_message(to_spend, pk, sequence, txouts) -> bytes:
    return sha256d(
        serialize(to_spend) + str(sequence) +
        binascii.hexlify(pk).decode() + serialize(txouts)).encode()


#validates a block
# checks if
@with_lock(chain_lock)
def validate_block(block: Block) -> Block:
    if not block.txns:
        raise BlockValidationError('txns empty')

    #check if block is to far in the future
    if block.timestamp - time.time() > Params.MAX_FUTURE_BLOCK_TIME:
        raise BlockValidationError('Block timestamp too far in future')

    #checks to see if the target difficulty isnt met
    if int(block.id, 16) > (1 << (256 - block.bits)):
        raise BlockValidationError("Block header doesn't satisfy bits")

    #checks if any other transaction other than the first transaction is the coinbase
    if [i for (i, tx) in enumerate(block.txns) if tx.is_coinbase] != [0]:
        raise BlockValidationError('First txn must be coinbase and no more')

    #validate each transaction in block
    try:
        for i, txn in enumerate(block.txns):
            txn.validate_basics(as_coinbase=(i == 0))#only the first transaction should be a coinbase
    except TxnValidationError:
        logger.exception(f"Transaction {txn} in {block} failed to validate")
        raise BlockValidationError('Invalid txn {txn.id}')

    #checks if merkle tree is correct
    if get_merkle_root_of_txns(block.txns).val != block.merkle_hash:
        raise BlockValidationError('Merkle hash invalid')

    #checks if checks to see if timestamp is to old
    if block.timestamp <= get_median_time_past(11):
        raise BlockValidationError('timestamp too old')

    if not block.prev_block_hash and not active_chain:
        # This is the genesis block.
        prev_block_chain_idx = ACTIVE_CHAIN_IDX
    else:
        prev_block, prev_block_height, prev_block_chain_idx = locate_block(
            block.prev_block_hash)

        if not prev_block:
            raise BlockValidationError(
                f'prev block {block.prev_block_hash} not found in any chain',
                to_orphan=block)

        # No more validation for a block getting attached to a branch.
        if prev_block_chain_idx != ACTIVE_CHAIN_IDX:
            return block, prev_block_chain_idx

        # Prev. block found in active chain, but isn't tip => new fork.
        elif prev_block != active_chain[-1]:
            return block, prev_block_chain_idx + 1  # Non-existent

    if get_next_work_required(block.prev_block_hash) != block.bits:
        raise BlockValidationError('bits is incorrect')

    for txn in block.txns[1:]:
        try:
            validate_txn(txn, siblings_in_block=block.txns[1:],
                         allow_utxo_from_mempool=False)
        except TxnValidationError:
            msg = f"{txn} failed to validate"
            logger.exception(msg)
            raise BlockValidationError(msg)

    return block, prev_block_chain_idx

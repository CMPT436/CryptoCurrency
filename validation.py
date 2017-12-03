def validate_txn(txn: Transaction,
                 as_coinbase: bool = False,
                 siblings_in_block: Iterable[Transaction] = None,
                 allow_utxo_from_mempool: bool = True,
                 ) -> Transaction:
    
def validate_signature_for_spend(txin, utxo: UnspentTxOut, txn):
    pass

def build_spend_message(to_spend, pk, sequence, txouts) -> bytes:
    pass


@with_lock(chain_lock)
def validate_block(block: Block) -> Block:
    pass

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

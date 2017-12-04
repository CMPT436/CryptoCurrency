# Wallet
# Wallet is a glorified name for storing and generating the private and public keys
#  of the transactions in the chain.
# 		- Bitcoin uses a sha256[signature ~unique 256-bit] and then a ripemd160[160 bit hash key],
#				for the wallet address generated off
#     - Wallet checks if there exists a path already or not
#		- 	If No path :
#			- creates a private signature key using Elliptical Curve Digital Signature Algorithm(ECDSA)
#			- derives a public verifying key off of the private signature key
#		-  If path exists :
#			- generates the signature key from Elliptical Curve Digital Signature Algorithm(ECDSA)
#		- Generates public verifying key from signing key
#		- Generates address from public key
#	
#	- returns private signing key, public verifying key, and the Wallet Address 
# ----------------------------------------------------------------------------

#
WALLET_PATH = os.environ.get('TC_WALLET_PATH', 'wallet.dat')

#encodes our 
def pubkey_to_address(pubkey: bytes) -> str:
    if 'ripemd160' not in hashlib.algorithms_available:
        raise RuntimeError('missing ripemd160 hash algorithm')

    s = hashlib.sha256(pubkey).digest()
    r = hashlib.new('ripemd160', s).digest()
    return b58encode_check(b'\x00' + r)


@lru_cache()
def init_wallet(path=None):
    path = path or WALLET_PATH

    if os.path.exists(path):
        with open(path, 'rb') as f:
            private_key = ecdsa.SigningKey.from_string(
                f.read(), curve=ecdsa.SECP256k1)
    else:
        logger.info(f"generating new wallet: '{path}'")
        private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
        with open(path, 'wb') as f:
            f.write(private_key.to_string())

    public_key = private_key.get_verifying_key()
    my_addy = pubkey_to_address(verifying_key.to_string())
    logger.info(f"your address is {my_address}")

    return private_key, public_key, my_addy


import os
from web3 import Web3

class NoveamBlockchain:
    def __init__(self):
        rpc_url = os.getenv("WEB3_RPC_URL")
        if not rpc_url:
            raise RuntimeError("WEB3_RPC_URL is missing")

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

    def get_chain_id(self):
        return self.w3.eth.chain_id

    def get_balance(self, address):
        if not Web3.is_address(address):
            raise ValueError("Invalid wallet address")

        address = Web3.to_checksum_address(address)
        balance = self.w3.eth.get_balance(address)

        return str(self.w3.from_wei(balance, "ether"))


import os
from web3 import Web3

class NoveamWeb3:
    def __init__(self):
        rpc_url = os.getenv("WEB3_RPC_URL")

        if not rpc_url:
            raise RuntimeError(
                "WEB3_RPC_URL is not configured"
            )

        self.web3 = Web3(
            Web3.HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": 10}
            )
        )

    def status(self):
        return {
            "connected": self.web3.is_connected(),
            "chain_id": (
                self.web3.eth.chain_id
                if self.web3.is_connected()
                else None
            )
        }

    def get_balance(self, address):
        if not Web3.is_address(address):
            raise ValueError("Invalid wallet address")

        checksum = Web3.to_checksum_address(address)

        balance_wei = self.web3.eth.get_balance(
            checksum
        )

        return {
            "address": checksum,
            "balance": str(
                self.web3.from_wei(balance_wei, "ether")
            )
        }

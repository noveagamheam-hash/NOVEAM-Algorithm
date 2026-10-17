
import secrets
import time
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


CHALLENGE_EXPIRY_SECONDS = 300

# Development-only storage.
# Production must use a shared persistent store.
_challenges = {}
_lock = threading.Lock()


@dataclass
class WalletChallenge:
    address: str
    message: str
    expires_at: float
    used: bool = False


def normalize_address(address: str) -> str:
    """Validate and normalize an EVM wallet address."""
    if not Web3.is_address(address):
        raise ValueError("Invalid wallet address")

    return Web3.to_checksum_address(address)


def create_wallet_challenge(
    address: str,
    domain: str = "noveam.in",
    chain_id: int = 56
) -> dict:
    """
    Create a one-time wallet signing challenge.

    chain_id=56 corresponds to BNB Smart Chain mainnet.
    """

    address = normalize_address(address)

    if domain != "noveam.in":
        raise ValueError("Unsupported authentication domain")

    if chain_id not in (1, 56, 97, 11155111):
        raise ValueError("Unsupported blockchain network")

    nonce = secrets.token_urlsafe(24)
    now = time.time()
    expires_at = now + CHALLENGE_EXPIRY_SECONDS

    issued_at = datetime.fromtimestamp(
        now, timezone.utc
    ).isoformat()

    expiration = datetime.fromtimestamp(
        expires_at, timezone.utc
    ).isoformat()

    message = (
        f"{domain} wants you to sign in with your "
        f"Ethereum account:\n"
        f"{address}\n\n"
        f"Sign in to NOVEAM.\n\n"
        f"URI: https://{domain}\n"
        f"Version: 1\n"
        f"Chain ID: {chain_id}\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}\n"
        f"Expiration Time: {expiration}"
    )

    challenge = WalletChallenge(
        address=address,
        message=message,
        expires_at=expires_at
    )

    with _lock:
        _challenges[nonce] = challenge

    return {
        "address": address,
        "nonce": nonce,
        "message": message,
        "expires_at": expiration,
        "chain_id": chain_id
    }


def verify_wallet_signature(
    nonce: str,
    signature: str
) -> dict:
    """
    Verify wallet ownership using a signed challenge.

    This function consumes the challenge once.
    """

    with _lock:
        challenge = _challenges.pop(nonce, None)

    if challenge is None:
        raise ValueError(
            "Challenge not found, expired, or already used"
        )

    if time.time() > challenge.expires_at:
        raise ValueError("Wallet challenge expired")

    try:
        encoded_message = encode_defunct(
            text=challenge.message
        )

        recovered_address = Account.recover_message(
            encoded_message,
            signature=signature
        )

        recovered_address = normalize_address(
            recovered_address
        )

    except Exception as exc:
        raise ValueError(
            "Invalid wallet signature"
        ) from exc

    if recovered_address != challenge.address:
        raise ValueError(
            "Wallet signature does not match"
        )

    return {
        "verified": True,
        "address": recovered_address,
        "authenticated_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

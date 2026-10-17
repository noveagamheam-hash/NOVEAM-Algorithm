
"""
NOVEAM Web3 API Routes
Version: 0.1.0

FastAPI integration for:
- Blockchain status and balances
- Wallet signing challenges
- Wallet ownership verification
- Authenticated wallet linking
- Wallet listing and unlinking
- Public IPFS uploads

Production authentication must be configured
before enabling protected endpoints.
"""

import os
import secrets
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from noveam_web3.wallet_auth import (
    create_wallet_challenge,
    verify_wallet_signature,
)
from noveam_web3.identity import (
    NoveamIdentity,
    IdentityError,
)
from noveam_web3.ipfs import (
    NoveamIPFS,
    IPFSError,
    MAX_FILE_SIZE,
)

router = APIRouter(
    prefix="/api/web3",
    tags=["NOVEAM Web3"]
)


# -----------------------------------
# Request models
# -----------------------------------

class WalletChallengeRequest(BaseModel):
    address: str
    chain_id: int = 56


class WalletVerifyRequest(BaseModel):
    nonce: str = Field(min_length=1)
    signature: str = Field(min_length=1)


class WalletLinkRequest(BaseModel):
    nonce: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    chain_id: int = 56


# -----------------------------------
# Authentication integration
# -----------------------------------

async def get_current_user_id() -> str:
    """
    SECURITY PLACEHOLDER.

    Replace with trusted Firebase ID-token
    verification or your existing authenticated
    NOVEAM backend identity dependency.

    Never accept a client-supplied user ID.
    """
    raise HTTPException(
        status_code=503,
        detail="NOVEAM authentication not configured"
    )


# -----------------------------------
# Identity service
# -----------------------------------

def get_identity_service() -> NoveamIdentity:
    """
    Development-only local identity store.

    Production requires durable shared storage.
    """
    if os.getenv("NDI_ENABLE_DEV_IDENTITY") != "true":
        raise HTTPException(
            status_code=503,
            detail="Identity storage not configured"
        )

    identity = NoveamIdentity()
    identity.initialize()
    return identity


# -----------------------------------
# Blockchain status
# -----------------------------------

@router.get("/status")
def web3_status():
    rpc_configured = bool(
        os.getenv("WEB3_RPC_URL")
    )

    return {
        "service": "NOVEAM Web3",
        "version": "0.1.0",
        "status": "running",
        "rpc_configured": rpc_configured,
        "wallet_auth": "prototype",
        "identity": "integration_pending",
    }


@router.get("/balance/{address}")
def wallet_balance(address: str):
    try:
        from noveam_web3.blockchain import (
            NoveamBlockchain
        )

        blockchain = NoveamBlockchain()

        return {
            "address": address,
            "chain_id": blockchain.get_chain_id(),
            "balance": blockchain.get_balance(
                address
            ),
        }

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid wallet address"
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Blockchain service unavailable"
        )


# -----------------------------------
# Wallet challenge
# -----------------------------------

@router.post("/wallet/challenge")
def wallet_challenge(
    request: WalletChallengeRequest
):
    try:
        return create_wallet_challenge(
            address=request.address,
            domain="noveam.in",
            chain_id=request.chain_id
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# -----------------------------------
# Wallet signature verification
# -----------------------------------

@router.post("/wallet/verify")
def wallet_verify(
    request: WalletVerifyRequest
):
    try:
        return verify_wallet_signature(
            nonce=request.nonce,
            signature=request.signature
        )

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired wallet proof"
        )


# -----------------------------------
# Link wallet to NOVEAM account
# -----------------------------------

@router.post("/wallet/link")
def link_wallet(
    request: WalletLinkRequest,
    user_id: str = Depends(get_current_user_id),
    identity: NoveamIdentity = Depends(
        get_identity_service
    )
):
    """
    Requires a verified NOVEAM user.

    A fresh challenge is consumed during linking.
    """

    try:
        proof = verify_wallet_signature(
            nonce=request.nonce,
            signature=request.signature
        )

        result = identity.link_wallet(
            user_id=user_id,
            wallet_address=proof["address"],
            chain_id=request.chain_id,
            verified=True
        )

        return result

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid wallet signature"
        )

    except IdentityError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc)
        )


# -----------------------------------
# List linked wallets
# -----------------------------------

@router.get("/wallets")
def list_wallets(
    user_id: str = Depends(get_current_user_id),
    identity: NoveamIdentity = Depends(
        get_identity_service
    )
):
    return {
        "wallets": identity.get_user_wallets(
            user_id
        )
    }


# -----------------------------------
# Unlink wallet
# -----------------------------------

@router.delete("/wallet/{address}")
def unlink_wallet(
    address: str,
    user_id: str = Depends(get_current_user_id),
    identity: NoveamIdentity = Depends(
        get_identity_service
    )
):
    try:
        return identity.unlink_wallet(
            user_id=user_id,
            wallet_address=address
        )

    except IdentityError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


# -----------------------------------
# Upload public content to IPFS
# -----------------------------------

@router.post("/ipfs/upload")
async def upload_ipfs(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Development integration only.

    Requires authentication.
    Production also needs quotas, malware
    scanning, content validation and moderation.
    """

    if os.getenv("NDI_ENABLE_IPFS_UPLOAD") != "true":
        raise HTTPException(
            status_code=503,
            detail="IPFS uploads are disabled"
        )

    data = await file.read(MAX_FILE_SIZE + 1)

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds size limit"
        )

    try:
        ipfs = NoveamIPFS()

        result = await ipfs.upload_bytes(
            data=data,
            filename=file.filename or "upload",
            mime_type=file.content_type or ""
        )

        return {
            "cid": result.cid,
            "filename": result.filename,
            "size": result.size,
            "gateway_url": result.gateway_url
        }

    except IPFSError:
        raise HTTPException(
            status_code=502,
            detail="IPFS operation failed"
        )

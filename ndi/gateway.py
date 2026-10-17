import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from .models import RankRequest, RankResponse
from .ranking import rank

router = APIRouter(prefix='/api/ndi', tags=['NDI'])

def require_user():
    # Replace with your EXISTING Firebase token verification dependency.
    # Fail closed until wired; never trust user IDs sent by clients.
    raise HTTPException(503, 'Connect existing Firebase authentication dependency')

@router.post('/rank', response_model=RankResponse)
async def rank_gateway(payload: RankRequest, user=Depends(require_user)):
    url = os.environ.get('NDI_NODE_URL')
    key = os.environ.get('NDI_NODE_KEY')
    if not url:
        return rank(payload)
    if not key or not url.startswith('https://'):
        raise HTTPException(503, 'Secure NDI node configuration required')
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            result = await client.post(url.rstrip('/') + '/v1/rank', json=payload.model_dump(), headers={'X-Node-Key': key})
            result.raise_for_status()
            parsed = RankResponse.model_validate(result.json())
            allowed = {p.id for p in payload.posts if p.visible and (payload.mode != 'following' or p.followed)}
            ids = [p.id for p in parsed.results]
            if len(ids) != len(set(ids)) or set(ids) != allowed or parsed.algorithm != 'NDI-A01':
                raise ValueError('Invalid node ranking response')
            return parsed
    except (httpx.HTTPError, ValueError):
        # Local ranking is a safe fallback, provided posts were filtered by the gateway.
        return rank(payload)

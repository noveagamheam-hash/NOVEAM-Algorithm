import os
from fastapi import FastAPI, Header, HTTPException
from .models import RankRequest, RankResponse
from .ranking import rank

app = FastAPI(title='NOVEAM NDI Ranking Node')

@app.get('/health')
def health():
    return {'status': 'ok', 'algorithm': 'NDI-A01'}

@app.post('/v1/rank', response_model=RankResponse)
def rank_posts(payload: RankRequest, x_node_key: str | None = Header(default=None)):
    import hmac
    key = os.environ.get('NDI_NODE_KEY')
    if not key:
        raise HTTPException(503, 'Node key not configured')
    if not x_node_key or not hmac.compare_digest(x_node_key, key):
        raise HTTPException(401, 'Unauthorized')
    return rank(payload)

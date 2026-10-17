
from fastapi import FastAPI
from noveam_web3.routes import router as web3_router

# NOVEAM AI Ranking Algorithm
from ndi.models import RankRequest, RankResponse
from ndi.ranking import rank

app = FastAPI(
    title="NOVEAM Decentralized AI & Web3 API",
    description=(
        "NOVEAM Hybrid Decentralized AI "
        "and Web3 Backend Service"
    ),
    version="0.1.0"
)

# Register existing Web3 API routes
app.include_router(web3_router)


@app.get("/")
def root():
    return {
        "service": "NOVEAM Algorithm",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "NOVEAM Algorithm"
    }


# NOVEAM NDI-A01 AI Recommendation Endpoint
@app.post(
    "/api/ai/rank",
    response_model=RankResponse,
    tags=["NOVEAM AI"]
)
def rank_feed(request: RankRequest):
    return rank(request)

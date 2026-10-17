
from fastapi import FastAPI
from noveam_web3.routes import router as web3_router

app = FastAPI(
    title="NOVEAM Decentralized AI & Web3 API",
    description=(
        "NOVEAM Hybrid Decentralized AI "
        "and Web3 Backend Service"
    ),
    version="0.1.0"
)

# Register Web3 API routes
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

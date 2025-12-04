from fastapi import APIRouter

router = APIRouter()

@router.get("/perception/health")
def health():
    return {"status": "ok"}

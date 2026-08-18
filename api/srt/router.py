from fastapi import APIRouter
from api.srt.endpoint.srt_router import router

api_router = APIRouter()

api_router.include_router(router)

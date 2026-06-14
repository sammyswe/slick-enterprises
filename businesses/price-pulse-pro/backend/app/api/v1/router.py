from fastapi import APIRouter

from app.routes.competitors import router as competitors_router
from app.routes.products import router as products_router

router = APIRouter(prefix="/api/v1")
router.include_router(competitors_router)
router.include_router(products_router)

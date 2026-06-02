from fastapi import APIRouter

from app.api.routes.store import accounts, chatbot, commerce, customers, insights, inventory, purchases, reports, settings

router = APIRouter()
router.include_router(insights.router)
router.include_router(inventory.router)
router.include_router(customers.router)
router.include_router(commerce.router)
router.include_router(purchases.router)
router.include_router(accounts.router)
router.include_router(settings.router)
router.include_router(reports.router)
router.include_router(chatbot.router)

from .router import router
from .accounts import router as accounts_router
from .campaigns import router as campaigns_router
from .logs import router as logs_router

router.include_router(accounts_router)
router.include_router(campaigns_router)
router.include_router(logs_router)

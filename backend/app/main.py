from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.customer import router as customer_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Telegram Ads Platform",
        version="0.1.0",
    )

    # --------------------------------------------------
    # CORS (safe defaults, tighten later)
    # --------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # change in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------------------------------------
    # Routers
    # --------------------------------------------------
    app.include_router(admin_router)
    app.include_router(customer_router)

    # --------------------------------------------------
    # Health check
    # --------------------------------------------------
    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

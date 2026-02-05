import logging.config

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.dependency_injection.application_container import Application
from interface.api import chat_endpoints, health_router, webhook_whatsapp
from interface.websocket import chat_ws


def create_app() -> FastAPI:
    """
    Cria e configura a aplicação FastAPI.

    Returns:
        FastAPI: Aplicação configurada
    """
    settings = Settings()
    logging.config.dictConfig(settings.LOGGING.model_dump())

    container = Application()

    app = FastAPI(
        title="Chatbot Template API",
        version="1.0.0",
        description="Template base para chatbots com LangGraph, Bedrock e DynamoDB",
    )

    app.container = container

    container.wire(
        modules=[
            chat_endpoints,
            chat_ws,
            health_router,
            webhook_whatsapp,
        ]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_endpoints.router)
    app.include_router(chat_ws.router)
    app.include_router(health_router.router)
    app.include_router(webhook_whatsapp.router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8181)

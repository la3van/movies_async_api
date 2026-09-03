"""Маршрутизации API весрии 1."""

from api.v1.endpoints.events import router as events_router
from flask import Blueprint

api_router = Blueprint(
    "api_v1",
    __name__,
    url_prefix="/api/v1",
)

api_router.register_blueprint(
    events_router,
)

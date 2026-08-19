"""Маршрутизации API весрии 1."""
from flask import Blueprint

from api.v1.endpoints.events import router as events_router


api_router = Blueprint(
    "api_v1",
    __name__,
    url_prefix="/api/v1",
)

api_router.register_blueprint(
    events_router,
)

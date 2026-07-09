"""Роутеры для проверки прав доступа."""
from fastapi import APIRouter

router = APIRouter(
    prefix='/permissions',
    tags=['permissions'],
)

"""Роутеры для управления ролями."""
from fastapi import APIRouter

router = APIRouter(
    prefix='/roles',
    tags=['roles'],
)

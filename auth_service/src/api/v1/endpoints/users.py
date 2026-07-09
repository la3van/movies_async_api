"""Роутеры для работы с пользователями."""
from fastapi import APIRouter

router = APIRouter(
    prefix='/users',
    tags=['users'],
)

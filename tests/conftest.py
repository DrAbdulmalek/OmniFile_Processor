#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/conftest.py
=================

إعدادات pytest المشتركة.
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from api_server_v2.main import app
from api_server_v2.database import get_db, Base
from api_server_v2.models import User


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """إنشاء event loop للجلسة."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db() -> AsyncGenerator:
    """إنشاء قاعدة بيانات اختبار."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    # قاعدة بيانات في الذاكرة
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # إنشاء الجداول
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_session

    # تنظيف
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_db):
    """جلسة قاعدة بيانات للاختبار."""
    async with test_db() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """عميل اختبار متزامن."""
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """عميل اختبار غير متزامن."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_image() -> Path:
    """صورة نموذجية للاختبار."""
    return Path("tests/fixtures/sample_arabic_text.jpg")


@pytest.fixture
def sample_handwriting() -> Path:
    """صورة خط يد نموذجية."""
    return Path("tests/fixtures/sample_handwriting.jpg")


@pytest.fixture
def auth_headers() -> dict:
    """Headers مصادقة للاختبار."""
    return {"Authorization": "Bearer test-token"}


@pytest_asyncio.fixture
async def test_user(db_session):
    """مستخدم نموذجي للاختبار."""
    user = User(
        email="test@omnifile.app",
        username="testuser",
        hashed_password="hashed",
        is_active=True,
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    return user

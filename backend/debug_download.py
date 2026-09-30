import asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import create_app
from app.models.request import Request, RequestStatus
from app.models.deliverable import Deliverable, DeliverableStatus
from app.models.student import Student
from app.services.auth import hash_password, create_session_token, SESSION_COOKIE_NAME
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.models import *

async def test():
    engine = create_async_engine(
        'sqlite+aiosqlite:///:memory:',
        echo=True,
        poolclass=StaticPool,
        connect_args={'check_same_thread': False},
    )
    async with engine.begin() as conn:
        from app.db.session import Base
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    # Create test data
    async with factory() as session:
        student = Student(
            id=uuid.uuid4(),
            email='test@test.com',
            display_name='Test User',
            password_hash='hash',
            role='student',
            status='active',
            credit_balance=1000.0,
        )
        session.add(student)
        await session.flush()

        request = Request(
            student_id=student.id,
            feature='presentation',
            intent='presentation',
            model_tier='default',
            status=RequestStatus.READY,
            request_payload_hash='abc123',
        )
        session.add(request)
        await session.flush()

        deliverable = Deliverable(
            request_id=request.id,
            student_id=student.id,
            file_type='pptx',
            storage_object_key=f'presentations/{student.id}/{uuid.uuid4()}.pptx',
            mime_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            file_size=1024,
            renderer_version='1.0.0',
            schema_version='1.0.0',
            input_hash='abc123',
            status=DeliverableStatus.READY,
        )
        session.add(deliverable)
        await session.commit()
        await session.refresh(deliverable)

        print(f'Deliverable ID: {deliverable.id}')
        deliverable_id = deliverable.id
        student_id = student.id

    # Now test with API
    app = create_app()

    async def db_session():
        from sqlalchemy.ext.asyncio import async_sessionmaker
        async with async_sessionmaker(bind=engine, expire_on_commit=False)() as session:
            yield session

    from app.db.session import get_db
    app.dependency_overrides[get_db] = lambda: db_session()

    from httpx import AsyncClient, ASGITransport
    from app.services.auth import create_session_token, SESSION_COOKIE_NAME

    token = create_session_token(student_id, 'student')
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://test',
        cookies={'session': token},
    ) as client:
        response = await client.get(f'/api/v1/deliverables/{deliverable_id}/download')
        print(f'Status: {response.status_code}')
        print(f'Response: {response.text}')

asyncio.run(test())
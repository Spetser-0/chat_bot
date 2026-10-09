
import asyncio
from app.db.session import Base, get_engine
from alembic.config import Config
from alembic import command
import os
# Register all models for create_all to find them
import app.models

async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized.")

def stamp_alembic():
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    print("Alembic stamped.")

if __name__ == "__main__":
    asyncio.run(init_db())
    stamp_alembic()

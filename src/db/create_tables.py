import sys
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.models.contact_model import Base
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

async def create_tables():
    engine = create_async_engine("sqlite+aiosqlite:///contacts.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables()) 
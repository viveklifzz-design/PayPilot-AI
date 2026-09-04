import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine
from app.db.base import Base

async def recreate():
    print("Recreating database tables from SQLAlchemy Base metadata...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables recreated successfully!")

if __name__ == "__main__":
    asyncio.run(recreate())

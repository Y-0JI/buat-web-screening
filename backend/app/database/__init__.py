from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

is_sqlite = settings.database_url.startswith("sqlite")

engine = create_async_engine(
    settings.database_url,
    echo=False,
    **({} if is_sqlite else {"pool_size": 5, "max_overflow": 10}),
)

if is_sqlite:
    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_enable_fk(dbapi_connection, _record):
        # SQLite tidak menegakkan foreign key secara default; nyalakan per koneksi
        # agar ON DELETE CASCADE (mis. accumulation_signals) benar-benar bekerja.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
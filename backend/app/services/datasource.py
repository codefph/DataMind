from urllib.parse import quote_plus

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..core.security import decrypt_secret, encrypt_secret
from ..models.datasource import Datasource
from ..schemas.datasource import DatasourceCreate, TestResult

DRIVERS: dict[str, str] = {
    "postgresql": "postgresql+asyncpg",
    "mysql": "mysql+asyncmy",
    "mariadb": "mysql+asyncmy",
    "clickhouse": "clickhouse+asynch",
    "sqlite": "sqlite+aiosqlite",
}


def build_url(ds: Datasource) -> str:
    driver = DRIVERS.get(ds.type)
    if not driver:
        raise ValueError(f"不支持的数据源类型: {ds.type}")
    if ds.type == "sqlite":
        return f"{driver}:///{quote_plus(ds.database)}"
    user = quote_plus(ds.username)
    password = quote_plus(decrypt_secret(ds.password_encrypted))
    database = quote_plus(ds.database)
    return f"{driver}://{user}:{password}@{ds.host}:{ds.port}/{database}"


async def create_datasource(session: AsyncSession, data: DatasourceCreate) -> Datasource:
    ds = Datasource(
        name=data.name,
        type=data.type,
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        password_encrypted=encrypt_secret(data.password),
        default_schema=data.default_schema,
        extra_params=data.extra_params,
    )
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return ds


async def list_datasources(session: AsyncSession) -> list[Datasource]:
    result = await session.execute(select(Datasource).order_by(Datasource.id))
    return list(result.scalars().all())


async def get_datasource(session: AsyncSession, ds_id: int) -> Datasource | None:
    return await session.get(Datasource, ds_id)


async def delete_datasource(session: AsyncSession, ds_id: int) -> None:
    ds = await session.get(Datasource, ds_id)
    if ds is not None:
        await session.delete(ds)
        await session.commit()


async def test_connection(ds: Datasource) -> TestResult:
    url = build_url(ds)
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return TestResult(ok=True, message="连接成功")
    except Exception as exc:  # noqa: BLE001
        return TestResult(ok=False, message=f"{type(exc).__name__}: {exc}")
    finally:
        await engine.dispose()


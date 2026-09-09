from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """所有 SQLite 表的声明基类；启动时由 API lifespan 创建真实数据表。"""
    pass


def build_engine(database_url: str | None = None):
    # 默认 URL 指向项目 data/ 下的真实 SQLite 文件；测试会显式传入内存数据库。
    url = database_url or get_settings().database_url
    return create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """每个 HTTP 请求独享一个会话，结束后确保释放连接。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database_schema() -> None:
    """根据当前 ORM 模型创建缺失的数据表。"""
    Base.metadata.create_all(bind=engine)

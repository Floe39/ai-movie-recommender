from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.config import PROJECT_ROOT, Settings
from app.repository import Repository
from app.schemas import WatchStatus


def test_watchlist_can_add_update_and_delete():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        repo = Repository(db)
        item = repo.save_watchlist_item(603, WatchStatus.WANT_TO_WATCH, "周末看")
        updated = repo.save_watchlist_item(603, WatchStatus.WATCHED, "已看")

        assert item.movie_tmdb_id == 603
        assert updated.status == WatchStatus.WATCHED.value
        assert repo.delete_watchlist_item(603) is True
        assert repo.list_watchlist() == []


def test_sqlite_file_persists_watchlist_across_sessions(tmp_path):
    """这里使用真实 SQLite 文件，不是内存数据库，验证重开连接后仍可读到片单。"""
    engine = create_engine(f"sqlite:///{tmp_path / 'movie_recommender.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        Repository(db).save_watchlist_item(238, WatchStatus.WANT_TO_WATCH, "持久化验证")

    with Session(engine) as db:
        restored = Repository(db).get_watchlist_item(238)
        assert restored is not None
        assert restored.note == "持久化验证"


def test_relative_sqlite_url_is_resolved_from_project_root():
    settings = Settings(database_url="sqlite:///./data/portable_test.db")
    assert settings.database_url == f"sqlite:///{PROJECT_ROOT / 'data' / 'portable_test.db'}"

"""创建本项目的真实 SQLite 数据表。

从项目根目录运行：python backend/init_db.py
数据库文件默认生成到 data/movie_recommender.db；可通过 DATABASE_URL 改为其他位置或数据库。
"""

# 导入 models 是必要的：这样 SQLAlchemy 才会把所有表登记到 Base.metadata 中。
import app.models  # noqa: F401
from app.config import get_settings
from app.database import Base, create_database_schema


def main() -> None:
    create_database_schema()
    print(f"数据库已初始化：{get_settings().database_url}")
    print(f"已创建/确认数据表：{', '.join(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    main()

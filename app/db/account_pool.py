# coding:utf-8
import sys
import os
from sqlalchemy import create_engine, Column, Integer, String, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import event
from random import choice
from loguru import logger

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

DB_PATH = os.path.join(BASE_DIR, 'accounts.db')
DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={'timeout': 30})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


class OlibAccount(Base):
    __tablename__ = "tb_name"
    remix_id = Column(Integer, primary_key=True, index=True)
    remix_key = Column(String(50))
    num = Column(Integer)
    downloads_limit = Column(Integer, default=10)
    downloads_today = Column(Integer, default=0)


def _migrate_db():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(tb_name)"))
            columns = [row[1] for row in result]
            if 'downloads_limit' not in columns:
                conn.execute(text("ALTER TABLE tb_name ADD COLUMN downloads_limit INTEGER DEFAULT 10"))
                conn.commit()
                logger.info("Added downloads_limit column")
            if 'downloads_today' not in columns:
                conn.execute(text("ALTER TABLE tb_name ADD COLUMN downloads_today INTEGER DEFAULT 0"))
                conn.commit()
                logger.info("Added downloads_today column")
    except Exception as e:
        logger.error(f"Migration error: {e}")


def init_db():
    if os.path.exists(DB_PATH):
        logger.info(f"Loading existing database: {DB_PATH}")
    else:
        logger.info(f"Database not found, creating new: {DB_PATH}")
    Base.metadata.create_all(bind=engine)
    _migrate_db()
    logger.info("Database initialized successfully")


init_db()


class AccountPool:
    def __init__(self):
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()

    def get_one(self):
        try:
            result = self.db.query(OlibAccount).filter(OlibAccount.num > 0).all()
            if result:
                account = choice(result)
                return {
                    'remix_id': account.remix_id,
                    'remix_key': account.remix_key,
                    'num': account.num
                }
            logger.info("No available account with num > 0")
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving account: {e}")
            self.db.rollback()
        return None

    def reserve_account(self):
        try:
            row = self.db.execute(
                text("SELECT remix_id, remix_key FROM tb_name WHERE num > 0 ORDER BY RANDOM() LIMIT 1")
            ).first()
            if not row:
                logger.info("No available account with num > 0")
                return None
            updated = self.db.query(OlibAccount).filter(
                OlibAccount.remix_id == row.remix_id,
                OlibAccount.num > 0
            ).update({OlibAccount.num: OlibAccount.num - 1})
            self.db.commit()
            if updated:
                return {'remix_id': row.remix_id, 'remix_key': row.remix_key}
            return self.reserve_account()
        except SQLAlchemyError as e:
            logger.error(f"Error reserving account: {e}")
            self.db.rollback()
        return None

    def get_all(self):
        try:
            accounts = self.db.query(OlibAccount).all()
            return [
                {
                    'remix_id': a.remix_id,
                    'remix_key': a.remix_key,
                    'num': a.num,
                    'downloads_limit': a.downloads_limit,
                    'downloads_today': a.downloads_today,
                }
                for a in accounts
            ]
        except SQLAlchemyError as e:
            logger.error(f"Error fetching all accounts: {e}")
            self.db.rollback()
        return []

    def add_account(self, remix_id: int, remix_key: str, num: int = 10,
                    downloads_limit: int = 10, downloads_today: int = 0):
        try:
            existing = self.db.query(OlibAccount).filter_by(remix_id=remix_id).first()
            if existing:
                existing.remix_key = remix_key
                existing.num = num
                existing.downloads_limit = downloads_limit
                existing.downloads_today = downloads_today
            else:
                account = OlibAccount(
                    remix_id=remix_id, remix_key=remix_key, num=num,
                    downloads_limit=downloads_limit, downloads_today=downloads_today,
                )
                self.db.add(account)
            self.db.commit()
            logger.info(f"Account {remix_id} added/updated")
        except SQLAlchemyError as e:
            logger.error(f"Error adding account: {e}")
            self.db.rollback()

    def delete_account(self, remix_id: int):
        try:
            account = self.db.query(OlibAccount).filter_by(remix_id=remix_id).first()
            if account:
                self.db.delete(account)
                self.db.commit()
                logger.info(f"Account {remix_id} deleted")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting account: {e}")
            self.db.rollback()

    def decrement_num(self, remix_id: int):
        try:
            updated = self.db.query(OlibAccount).filter(
                OlibAccount.remix_id == remix_id,
                OlibAccount.num > 0
            ).update({OlibAccount.num: OlibAccount.num - 1})
            self.db.commit()
            if updated:
                logger.info(f"Account {remix_id} num decremented")
        except SQLAlchemyError as e:
            logger.error(f"Error decrementing account: {e}")
            self.db.rollback()

    def update_num(self, remix_id: int, num: int):
        try:
            account = self.db.query(OlibAccount).filter_by(remix_id=remix_id).first()
            if account:
                account.num = num
                self.db.commit()
                logger.info(f"Account {remix_id} num updated to {num}")
        except SQLAlchemyError as e:
            logger.error(f"Error updating account: {e}")
            self.db.rollback()

    def update_limits(self, remix_id: int, downloads_limit: int, downloads_today: int):
        try:
            account = self.db.query(OlibAccount).filter_by(remix_id=remix_id).first()
            if account:
                account.downloads_limit = downloads_limit
                account.downloads_today = downloads_today
                account.num = max(0, downloads_limit - downloads_today)
                self.db.commit()
                logger.info(f"Account {remix_id} limits updated: {downloads_limit}/{downloads_today}")
        except SQLAlchemyError as e:
            logger.error(f"Error updating account limits: {e}")
            self.db.rollback()

    def __del__(self):
        try:
            self.db.close()
        except Exception:
            pass

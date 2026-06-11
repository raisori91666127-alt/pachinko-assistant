from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./pachislot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Store(Base):
    __tablename__ = "stores"
    id = Column(Integer, primary_key=True)
    site7_id = Column(String, unique=True, index=True)
    name = Column(String)
    area = Column(String)


class MachineData(Base):
    __tablename__ = "machine_data"
    id = Column(Integer, primary_key=True)
    store_id = Column(String, index=True)
    date = Column(Date, index=True)
    machine_type = Column(String)   # 機種名
    unit_number = Column(Integer)   # 台番号
    games = Column(Integer)         # ゲーム数
    bb_count = Column(Integer)      # BB回数
    rb_count = Column(Integer)      # RB回数
    diff_medals = Column(Integer)   # 差枚数
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

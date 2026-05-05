"""B9 fixture 自检专用 throwaway model；M01 落地时连同对应 migration 一并删除。"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from api.models.base import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(String(200), nullable=False)

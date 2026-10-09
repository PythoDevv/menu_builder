from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # kim taklif qilgan (taklif havolasidagi tg_id). Faqat yangi kelganda yoziladi.
    referred_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    # False -> botni bloklagan
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Admin(Base):
    """Paneldan qo'shilgan admin. .env dagi ADMINS bu yerga yozilmaydi."""

    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="", server_default="")
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # kim qo'shgan (tg_id)
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    invite_link: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Majburiy obuna inline tugmasida kanal nomidan oldin chiqadigan premium emoji.
    icon_custom_emoji_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # True -> yopiq kanal (qo'shilish so'rovi yuboriladi)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SubscriptionButton(Base):
    """Majburiy obuna postidagi kanalga bog'liq bo'lmagan URL tugma."""

    __tablename__ = "subscription_buttons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(64))
    url: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class JoinRequest(Base):
    """Yopiq kanalga tashlangan qo'shilish so'rovi (Telegram API buni ko'rsatmaydi)."""

    __tablename__ = "join_requests"
    __table_args__ = (UniqueConstraint("user_tg_id", "channel_id", name="uq_join_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MenuItem(Base):
    """Menyu tugmasi. parent_id=None -> asosiy menyu."""

    __tablename__ = "menu_items"
    __table_args__ = (
        CheckConstraint("row_size BETWEEN 1 AND 4", name="ck_menu_items_row_size"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Tugmani ochish uchun kerakli taklif soni. 0 -> shartsiz ochiladi.
    required_referrals: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Telegram tugma uslubi: primary / success / danger. None -> oddiy.
    button_style: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    # Tugma matnidan alohida ko'rsatiladigan Telegram Premium custom emoji.
    icon_custom_emoji_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Shu tugma qatorida nechta bir xil turdagi tugma joylashishi kerak (1..4).
    # Yangi tugmalar standart holatda qatorda 2 tadan chiqadi.
    row_size: Mapped[int] = mapped_column(Integer, default=2, server_default="2")


class Content(Base):
    """Tugma ichidagi tayyor kontent: file_id + formatlangan matn/entitylar."""

    __tablename__ = "contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), index=True
    )
    # text / photo / video / document / audio / voice / animation / video_note / sticker
    type: Mapped[str] = mapped_column(String(20))
    file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Eski yozuvlarda HTML; yangi yozuvlarda tg_entities_v1 JSON formati.
    text_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Setting(Base):
    """Oddiy key-value sozlamalar (start xabar, telefon so'rash va h.k.)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

"""Bazaga barcha murojaatlar shu yerda. Har bir funksiya o'z sessiyasini ochadi."""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import TIMEZONE
from db.base import session_maker
from db.models import Admin, Channel, Content, JoinRequest, MenuItem, Setting, User

TZ = ZoneInfo(TIMEZONE)

# ---------------------------------------------------------------- sozlama kalitlari
K_START_TYPE = "start_type"
K_START_FILE = "start_file_id"
K_START_TEXT = "start_text"
K_ASK_PHONE = "ask_phone"
K_SUB_TYPE = "sub_type"
K_SUB_FILE = "sub_file_id"
K_SUB_TEXT = "sub_text"


# ============================================================================ USERS
async def get_or_create_user(tg_id: int, full_name: str, username: Optional[str]) -> User:
    async with session_maker() as s:
        user = await s.scalar(select(User).where(User.tg_id == tg_id))
        if user is None:
            user = User(tg_id=tg_id, full_name=full_name, username=username)
            s.add(user)
            await s.commit()
        elif (
            user.full_name != full_name
            or user.username != username
            or not user.is_active
        ):
            user.full_name = full_name
            user.username = username
            user.is_active = True
            await s.commit()
        return user


async def get_user(tg_id: int) -> Optional[User]:
    async with session_maker() as s:
        return await s.scalar(select(User).where(User.tg_id == tg_id))


async def set_phone(tg_id: int, phone: str) -> None:
    async with session_maker() as s:
        await s.execute(update(User).where(User.tg_id == tg_id).values(phone=phone))
        await s.commit()


async def set_user_active(tg_id: int, is_active: bool) -> None:
    async with session_maker() as s:
        await s.execute(update(User).where(User.tg_id == tg_id).values(is_active=is_active))
        await s.commit()


async def get_active_user_ids() -> list[int]:
    async with session_maker() as s:
        rows = await s.scalars(select(User.tg_id).where(User.is_active.is_(True)))
        return list(rows)


async def get_all_users() -> list[User]:
    async with session_maker() as s:
        rows = await s.scalars(select(User).order_by(User.id))
        return list(rows)


async def get_stats() -> dict:
    now = datetime.now(TZ)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    async with session_maker() as s:
        total = await s.scalar(select(func.count(User.id)))
        active = await s.scalar(select(func.count(User.id)).where(User.is_active.is_(True)))
        today = await s.scalar(
            select(func.count(User.id)).where(User.created_at >= day_start)
        )
        week = await s.scalar(select(func.count(User.id)).where(User.created_at >= week_start))
        with_phone = await s.scalar(
            select(func.count(User.id)).where(User.phone.is_not(None))
        )
    return {
        "total": total or 0,
        "active": active or 0,
        "today": today or 0,
        "week": week or 0,
        "with_phone": with_phone or 0,
    }


# =========================================================================== ADMINS
async def get_admins() -> list[Admin]:
    async with session_maker() as s:
        return list(await s.scalars(select(Admin).order_by(Admin.id)))


async def get_admin_ids() -> list[int]:
    async with session_maker() as s:
        return list(await s.scalars(select(Admin.tg_id)))


async def get_admin(admin_id: int) -> Optional[Admin]:
    async with session_maker() as s:
        return await s.get(Admin, admin_id)


async def get_admin_by_tg_id(tg_id: int) -> Optional[Admin]:
    async with session_maker() as s:
        return await s.scalar(select(Admin).where(Admin.tg_id == tg_id))


async def add_admin(
    tg_id: int, full_name: str, username: Optional[str], added_by: Optional[int]
) -> tuple[Admin, bool]:
    """(admin, yangi_qo'shildimi) qaytaradi."""
    async with session_maker() as s:
        admin = await s.scalar(select(Admin).where(Admin.tg_id == tg_id))
        if admin is not None:
            return admin, False
        admin = Admin(
            tg_id=tg_id, full_name=full_name, username=username, added_by=added_by
        )
        s.add(admin)
        await s.commit()
        return admin, True


async def delete_admin(admin_id: int) -> Optional[int]:
    """O'chirilgan adminning tg_id sini qaytaradi (topilmasa None)."""
    async with session_maker() as s:
        admin = await s.get(Admin, admin_id)
        if admin is None:
            return None
        tg_id = admin.tg_id
        await s.delete(admin)
        await s.commit()
        return tg_id


# ========================================================================= CHANNELS
async def get_channels(active_only: bool = False) -> list[Channel]:
    async with session_maker() as s:
        q = select(Channel).order_by(Channel.id)
        if active_only:
            q = q.where(Channel.is_active.is_(True))
        return list(await s.scalars(q))


async def get_channel(channel_id: int) -> Optional[Channel]:
    async with session_maker() as s:
        return await s.get(Channel, channel_id)


async def get_channel_by_chat_id(chat_id: int) -> Optional[Channel]:
    async with session_maker() as s:
        return await s.scalar(select(Channel).where(Channel.chat_id == chat_id))


async def add_channel(
    chat_id: int,
    title: str,
    username: Optional[str],
    invite_link: Optional[str],
    is_private: bool,
) -> Channel:
    async with session_maker() as s:
        ch = await s.scalar(select(Channel).where(Channel.chat_id == chat_id))
        if ch is None:
            ch = Channel(chat_id=chat_id)
            s.add(ch)
        ch.title = title
        ch.username = username
        ch.invite_link = invite_link
        ch.is_private = is_private
        ch.is_active = True
        await s.commit()
        return ch


async def toggle_channel(channel_id: int) -> Optional[Channel]:
    async with session_maker() as s:
        ch = await s.get(Channel, channel_id)
        if ch:
            ch.is_active = not ch.is_active
            await s.commit()
        return ch


async def delete_channel(channel_id: int) -> None:
    async with session_maker() as s:
        await s.execute(delete(Channel).where(Channel.id == channel_id))
        await s.commit()


# ==================================================================== JOIN REQUESTS
async def add_join_request(user_tg_id: int, channel_id: int) -> None:
    async with session_maker() as s:
        stmt = (
            pg_insert(JoinRequest)
            .values(user_tg_id=user_tg_id, channel_id=channel_id)
            .on_conflict_do_nothing(index_elements=["user_tg_id", "channel_id"])
        )
        await s.execute(stmt)
        await s.commit()


async def get_join_request_channel_ids(user_tg_id: int) -> set[int]:
    async with session_maker() as s:
        rows = await s.scalars(
            select(JoinRequest.channel_id).where(JoinRequest.user_tg_id == user_tg_id)
        )
        return set(rows)


# ======================================================================= MENU ITEMS
async def get_items(parent_id: Optional[int], active_only: bool = False) -> list[MenuItem]:
    async with session_maker() as s:
        q = select(MenuItem).order_by(MenuItem.position, MenuItem.id)
        q = q.where(MenuItem.parent_id.is_(None) if parent_id is None else MenuItem.parent_id == parent_id)
        if active_only:
            q = q.where(MenuItem.is_active.is_(True))
        return list(await s.scalars(q))


async def get_item(item_id: int) -> Optional[MenuItem]:
    async with session_maker() as s:
        return await s.get(MenuItem, item_id)


async def add_item(parent_id: Optional[int], title: str) -> MenuItem:
    async with session_maker() as s:
        cond = MenuItem.parent_id.is_(None) if parent_id is None else MenuItem.parent_id == parent_id
        last = await s.scalar(select(func.coalesce(func.max(MenuItem.position), 0)).where(cond))
        item = MenuItem(parent_id=parent_id, title=title, position=(last or 0) + 1)
        s.add(item)
        await s.commit()
        return item


async def rename_item(item_id: int, title: str) -> None:
    async with session_maker() as s:
        await s.execute(update(MenuItem).where(MenuItem.id == item_id).values(title=title))
        await s.commit()


async def toggle_item(item_id: int) -> Optional[MenuItem]:
    async with session_maker() as s:
        item = await s.get(MenuItem, item_id)
        if item:
            item.is_active = not item.is_active
            await s.commit()
        return item


async def delete_item(item_id: int) -> None:
    """Ichidagi tugmalar va kontentlar ham o'chadi (DB cascade)."""
    async with session_maker() as s:
        await s.execute(delete(MenuItem).where(MenuItem.id == item_id))
        await s.commit()


async def move_item(item_id: int, direction: int) -> None:
    """direction: -1 yuqoriga, +1 pastga."""
    async with session_maker() as s:
        item = await s.get(MenuItem, item_id)
        if item is None:
            return
        cond = (
            MenuItem.parent_id.is_(None)
            if item.parent_id is None
            else MenuItem.parent_id == item.parent_id
        )
        siblings = list(
            await s.scalars(select(MenuItem).where(cond).order_by(MenuItem.position, MenuItem.id))
        )
        # tartib raqamlarini tozalab chiqamiz
        for i, sib in enumerate(siblings, start=1):
            sib.position = i
        idx = next((i for i, sib in enumerate(siblings) if sib.id == item_id), None)
        new_idx = idx + direction if idx is not None else None
        if new_idx is not None and 0 <= new_idx < len(siblings):
            siblings[idx].position, siblings[new_idx].position = (
                siblings[new_idx].position,
                siblings[idx].position,
            )
        await s.commit()


async def count_children(item_id: int) -> int:
    async with session_maker() as s:
        return await s.scalar(
            select(func.count(MenuItem.id)).where(MenuItem.parent_id == item_id)
        ) or 0


async def get_item_path(item_id: Optional[int]) -> list[MenuItem]:
    """Tugmadan yuqoriga qarab yo'l (breadcrumb)."""
    path: list[MenuItem] = []
    async with session_maker() as s:
        current_id = item_id
        while current_id is not None and len(path) < 20:
            item = await s.get(MenuItem, current_id)
            if item is None:
                break
            path.append(item)
            current_id = item.parent_id
    return list(reversed(path))


# ========================================================================= CONTENTS
async def get_contents(item_id: int) -> list[Content]:
    async with session_maker() as s:
        return list(
            await s.scalars(
                select(Content)
                .where(Content.menu_item_id == item_id)
                .order_by(Content.position, Content.id)
            )
        )


async def count_contents(item_id: int) -> int:
    async with session_maker() as s:
        return await s.scalar(
            select(func.count(Content.id)).where(Content.menu_item_id == item_id)
        ) or 0


async def add_content(
    item_id: int, type_: str, file_id: Optional[str], text_html: Optional[str]
) -> Content:
    async with session_maker() as s:
        last = await s.scalar(
            select(func.coalesce(func.max(Content.position), 0)).where(
                Content.menu_item_id == item_id
            )
        )
        c = Content(
            menu_item_id=item_id,
            type=type_,
            file_id=file_id,
            text_html=text_html,
            position=(last or 0) + 1,
        )
        s.add(c)
        await s.commit()
        return c


async def get_content(content_id: int) -> Optional[Content]:
    async with session_maker() as s:
        return await s.get(Content, content_id)


async def delete_content(content_id: int) -> None:
    async with session_maker() as s:
        await s.execute(delete(Content).where(Content.id == content_id))
        await s.commit()


# ========================================================================= SETTINGS
async def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    async with session_maker() as s:
        row = await s.get(Setting, key)
        return row.value if row and row.value is not None else default


async def set_setting(key: str, value: Optional[str]) -> None:
    async with session_maker() as s:
        stmt = (
            pg_insert(Setting)
            .values(key=key, value=value)
            .on_conflict_do_update(index_elements=["key"], set_={"value": value})
        )
        await s.execute(stmt)
        await s.commit()


async def get_start_message() -> Optional[dict]:
    """Admin qo'ygan start xabar. Qo'yilmagan bo'lsa None."""
    type_ = await get_setting(K_START_TYPE)
    if not type_:
        return None
    return {
        "type": type_,
        "file_id": await get_setting(K_START_FILE),
        "text_html": await get_setting(K_START_TEXT),
    }


async def set_start_message(type_: str, file_id: Optional[str], text_html: Optional[str]) -> None:
    await set_setting(K_START_TYPE, type_)
    await set_setting(K_START_FILE, file_id)
    await set_setting(K_START_TEXT, text_html)


async def delete_start_message() -> None:
    await set_setting(K_START_TYPE, None)
    await set_setting(K_START_FILE, None)
    await set_setting(K_START_TEXT, None)


async def get_sub_message() -> Optional[dict]:
    """Admin qo'ygan majburiy obuna xabari. Qo'yilmagan bo'lsa None (standart ishlatiladi)."""
    type_ = await get_setting(K_SUB_TYPE)
    if not type_:
        return None
    return {
        "type": type_,
        "file_id": await get_setting(K_SUB_FILE),
        "text_html": await get_setting(K_SUB_TEXT),
    }


async def set_sub_message(type_: str, file_id: Optional[str], text_html: Optional[str]) -> None:
    await set_setting(K_SUB_TYPE, type_)
    await set_setting(K_SUB_FILE, file_id)
    await set_setting(K_SUB_TEXT, text_html)


async def delete_sub_message() -> None:
    """Standart matnga qaytaradi."""
    await set_setting(K_SUB_TYPE, None)
    await set_setting(K_SUB_FILE, None)
    await set_setting(K_SUB_TEXT, None)


async def is_phone_required() -> bool:
    return (await get_setting(K_ASK_PHONE, "0")) == "1"


async def toggle_phone_required() -> bool:
    new = not await is_phone_required()
    await set_setting(K_ASK_PHONE, "1" if new else "0")
    return new

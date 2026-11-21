"""Bazaga barcha murojaatlar shu yerda. Har bir funksiya o'z sessiyasini ochadi."""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from config import TIMEZONE
from db.base import session_maker
from db.models import (
    Admin,
    Channel,
    Content,
    JoinRequest,
    MenuItem,
    PrivateLinkGrant,
    Setting,
    SubscriptionButton,
    User,
)
from utils.user_status import BLOCKED, DEACTIVATED, NOT_STARTED

TZ = ZoneInfo(TIMEZONE)

#: Botga /start bosgan foydalanuvchi (faqat zayafka tashlaganlar emas)
STARTED = User.inactive_reason.is_distinct_from(NOT_STARTED)

# ---------------------------------------------------------------- sozlama kalitlari
K_START_TYPE = "start_type"
K_START_FILE = "start_file_id"
K_START_TEXT = "start_text"
K_ASK_PHONE = "ask_phone"
K_SUB_TYPE = "sub_type"
K_SUB_FILE = "sub_file_id"
K_SUB_TEXT = "sub_text"
K_SUB_CHECK_TEXT = "sub_check_text"
K_SUB_CHECK_ICON = "sub_check_icon_custom_emoji_id"
K_FORCE_SUB_ON_START = "force_sub_on_start"
K_REF_TEXT = "ref_text"
K_MY_POINTS_ENABLED = "my_points_enabled"
K_MY_POINTS_TEXT = "my_points_text"
K_MY_POINTS_STYLE = "my_points_style"
K_MY_POINTS_ICON = "my_points_icon_custom_emoji_id"
K_MY_POINTS_MESSAGE = "my_points_message"
K_RATING_ENABLED = "rating_enabled"
K_RATING_TEXT = "rating_text"
K_RATING_STYLE = "rating_style"
K_RATING_ICON = "rating_icon_custom_emoji_id"
K_RATING_MESSAGE = "rating_message"
K_RATING_ROW_SIZE = "rating_row_size"
K_WINNERS_LIMIT = "winners_limit"
# yopiq kanal linki (N ta taklif -> shaxsiy bir martalik havola)
K_PL_ENABLED = "private_link_enabled"
K_PL_CHAT_ID = "private_link_chat_id"
K_PL_CHAT_TITLE = "private_link_chat_title"
K_PL_NEED = "private_link_need"
K_PL_TYPE = "private_link_type"
K_PL_FILE = "private_link_file_id"
K_PL_TEXT = "private_link_text"
K_PL_BUTTON_TEXT = "private_link_button_text"
K_PL_BUTTON_ICON = "private_link_button_icon_custom_emoji_id"
# har bir yangi taklifda taklif qilganga boradigan tabrik
K_REF_NOTIFY_TEXT = "ref_notify_text"

DEFAULT_MY_POINTS_TEXT = "🏆 Ballarim"
DEFAULT_RATING_TEXT = "🏅 Reyting"
DEFAULT_SUB_CHECK_TEXT = "✅ A'zo bo'ldim"
BUTTON_STYLES = {"primary", "success", "danger"}
DEFAULT_WINNERS_LIMIT = 10
MAX_WINNERS_LIMIT = 20


# ============================================================================ USERS
async def get_or_create_user(
    tg_id: int, full_name: str, username: Optional[str], referrer_id: Optional[int] = None
) -> tuple[User, Optional[int]]:
    """(user, taklif_hisoblangan_odam_tg_id) qaytaradi.

    Faqat botning shaxsiy chatida yozgan (ya'ni /start bosgan) odam uchun chaqiriladi.

    Taklif faqat foydalanuvchi birinchi marta yozilayotganda hisoblanadi:
    eski foydalanuvchi boshqa havoladan kirsa ham qayta yozilmaydi. Bazada
    `not_started` bo'lib turgan odam (oldin faqat zayafka tashlagan) birinchi
    marta botga kirsa — u ham yangi foydalanuvchi sifatida qabul qilinadi.
    """
    async with session_maker() as s:
        user = await s.scalar(select(User).where(User.tg_id == tg_id))
        is_new = user is None or user.inactive_reason == NOT_STARTED
        referred_by = None
        if is_new and referrer_id is not None and referrer_id != tg_id:
            # taklif qilgan odam ham botning foydalanuvchisi bo'lishi kerak
            exists = await s.scalar(
                select(User.id).where(User.tg_id == referrer_id, STARTED)
            )
            referred_by = referrer_id if exists else None

        if user is None:
            user = User(
                tg_id=tg_id, full_name=full_name, username=username, referred_by=referred_by
            )
            s.add(user)
            await s.commit()
            return user, referred_by

        if is_new:
            # bugun/7 kunlik statistikada botga kirgan kuni bilan ko'rinsin
            user.created_at = datetime.now(TZ)
            if user.referred_by is None:
                user.referred_by = referred_by
            else:
                referred_by = None
        if (
            is_new
            or user.full_name != full_name
            or user.username != username
            or not user.is_active
        ):
            user.full_name = full_name
            user.username = username
            user.is_active = True
            user.inactive_reason = None
            await s.commit()
        return user, referred_by


async def get_user(tg_id: int) -> Optional[User]:
    async with session_maker() as s:
        return await s.scalar(select(User).where(User.tg_id == tg_id))


async def set_phone(tg_id: int, phone: str) -> None:
    async with session_maker() as s:
        await s.execute(update(User).where(User.tg_id == tg_id).values(phone=phone))
        await s.commit()


async def set_user_inactive(tg_id: int, reason: str) -> None:
    """Xabar yetib bormadi: is_active=False va sababi (utils.user_status)."""
    async with session_maker() as s:
        await s.execute(
            update(User)
            .where(User.tg_id == tg_id)
            .values(is_active=False, inactive_reason=reason)
        )
        await s.commit()


async def set_user_reachable(tg_id: int) -> None:
    """Botni blokdan chiqardi. Botni hech ochmagan (`not_started`) odamga tegmaydi —
    u /start bosganda `get_or_create_user` yangi foydalanuvchi sifatida yozadi."""
    async with session_maker() as s:
        await s.execute(
            update(User)
            .where(User.tg_id == tg_id, STARTED)
            .values(is_active=True, inactive_reason=None)
        )
        await s.commit()


async def get_active_user_ids() -> list[int]:
    async with session_maker() as s:
        rows = await s.scalars(select(User.tg_id).where(User.is_active.is_(True)))
        return list(rows)


async def get_all_users() -> list[User]:
    """Botga /start bosgan barcha foydalanuvchilar (Excel uchun)."""
    async with session_maker() as s:
        rows = await s.scalars(select(User).where(STARTED).order_by(User.id))
        return list(rows)


async def get_stats() -> dict:
    """Faqat botga /start bosganlar hisoblanadi — zayafka tashlaganlar kirmaydi."""
    now = datetime.now(TZ)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    def count(*conds):
        return func.count(User.id).filter(*conds) if conds else func.count(User.id)

    async with session_maker() as s:
        row = (
            await s.execute(
                select(
                    count(),
                    count(User.is_active.is_(True)),
                    count(User.inactive_reason == BLOCKED),
                    count(User.inactive_reason == DEACTIVATED),
                    count(User.created_at >= day_start),
                    count(User.created_at >= week_start),
                    count(User.phone.is_not(None)),
                    count(User.referred_by.is_not(None)),
                    func.count(func.distinct(User.referred_by)),
                ).where(STARTED)
            )
        ).one()
    keys = (
        "total", "active", "blocked", "deactivated",
        "today", "week", "with_phone", "referred", "inviters",
    )
    return {key: value or 0 for key, value in zip(keys, row)}


# ====================================================================== REFERRALLAR
async def get_referral_count(tg_id: int) -> int:
    """Shu odam nechta odamni taklif qilgan."""
    async with session_maker() as s:
        return await s.scalar(
            select(func.count(User.id)).where(User.referred_by == tg_id)
        ) or 0


async def get_referral_counts() -> dict[int, int]:
    """{taklif qilgan tg_id: nechta} — Excel va statistika uchun."""
    async with session_maker() as s:
        rows = await s.execute(
            select(User.referred_by, func.count(User.id))
            .where(User.referred_by.is_not(None))
            .group_by(User.referred_by)
        )
        return {tg_id: count for tg_id, count in rows}


async def get_top_referrers(limit: int = 5) -> list[tuple[User, int]]:
    """Eng ko'p odam taklif qilganlar."""
    async with session_maker() as s:
        rows = await s.execute(
            select(User.referred_by, func.count(User.id).label("cnt"))
            .where(User.referred_by.is_not(None))
            .group_by(User.referred_by)
            .order_by(func.count(User.id).desc(), User.referred_by.asc())
            .limit(limit)
        )
        pairs = list(rows)
        if not pairs:
            return []
        ids = [tg_id for tg_id, _ in pairs]
        users = {
            u.tg_id: u for u in await s.scalars(select(User).where(User.tg_id.in_(ids)))
        }
        return [(users[tg_id], count) for tg_id, count in pairs if tg_id in users]


async def reset_referral_points() -> int:
    """Barcha taklif ballarini nolga tushiradi va o'zgargan qatorlar sonini beradi.

    Chaqiruvchi bu funksiyadan oldin dump yaratishi shart. Alohida funksiya bo'lishi
    resetni bitta DB tranzaksiyasida bajarish va backup xatosida unga umuman
    tegmaslik imkonini beradi.
    """
    async with session_maker() as s:
        result = await s.execute(
            update(User)
            .where(User.referred_by.is_not(None))
            .values(referred_by=None)
        )
        await s.commit()
        return result.rowcount or 0


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


async def set_channel_icon(
    channel_id: int, icon_custom_emoji_id: Optional[str]
) -> None:
    """Majburiy obuna inline tugmasining premium emoji ikonkasini saqlaydi."""
    async with session_maker() as s:
        await s.execute(
            update(Channel)
            .where(Channel.id == channel_id)
            .values(icon_custom_emoji_id=icon_custom_emoji_id)
        )
        await s.commit()


async def delete_channel(channel_id: int) -> None:
    async with session_maker() as s:
        await s.execute(delete(Channel).where(Channel.id == channel_id))
        await s.commit()


# ========================================================== SUBSCRIPTION BUTTONS
async def get_subscription_buttons() -> list[SubscriptionButton]:
    async with session_maker() as s:
        query = select(SubscriptionButton).order_by(SubscriptionButton.id)
        return list(await s.scalars(query))


async def get_subscription_button(button_id: int) -> Optional[SubscriptionButton]:
    async with session_maker() as s:
        return await s.get(SubscriptionButton, button_id)


async def add_subscription_button(title: str, url: str) -> SubscriptionButton:
    async with session_maker() as s:
        button = SubscriptionButton(title=title, url=url)
        s.add(button)
        await s.commit()
        return button


async def delete_subscription_button(button_id: int) -> None:
    async with session_maker() as s:
        await s.execute(
            delete(SubscriptionButton).where(SubscriptionButton.id == button_id)
        )
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


async def add_item(
    parent_id: Optional[int],
    title: str,
    required_referrals: int = 0,
    icon_custom_emoji_id: Optional[str] = None,
    row_size: int = 2,
) -> MenuItem:
    if row_size not in {1, 2, 3, 4}:
        raise ValueError(f"Noto'g'ri qator o'lchami: {row_size}")
    async with session_maker() as s:
        cond = MenuItem.parent_id.is_(None) if parent_id is None else MenuItem.parent_id == parent_id
        last = await s.scalar(select(func.coalesce(func.max(MenuItem.position), 0)).where(cond))
        item = MenuItem(
            parent_id=parent_id,
            title=title,
            position=(last or 0) + 1,
            required_referrals=max(required_referrals, 0),
            icon_custom_emoji_id=icon_custom_emoji_id,
            row_size=row_size,
        )
        s.add(item)
        await s.commit()
        return item


async def set_item_referrals(item_id: int, count: int) -> None:
    """0 -> shart olib tashlanadi."""
    async with session_maker() as s:
        await s.execute(
            update(MenuItem)
            .where(MenuItem.id == item_id)
            .values(required_referrals=max(count, 0))
        )
        await s.commit()


async def set_item_style(item_id: int, style: Optional[str]) -> None:
    """Telegram tugma uslubi. None -> oddiy ko'rinish."""
    if style is not None and style not in BUTTON_STYLES:
        raise ValueError(f"Noto'g'ri tugma uslubi: {style}")
    async with session_maker() as s:
        await s.execute(
            update(MenuItem).where(MenuItem.id == item_id).values(button_style=style)
        )
        await s.commit()


async def set_item_row_size(item_id: int, row_size: int) -> None:
    """Tugma joylashadigan qatordagi tugmalar sonini (1..4) saqlaydi."""
    if row_size not in {1, 2, 3, 4}:
        raise ValueError(f"Noto'g'ri qator o'lchami: {row_size}")
    async with session_maker() as s:
        await s.execute(
            update(MenuItem).where(MenuItem.id == item_id).values(row_size=row_size)
        )
        await s.commit()


async def rename_item(
    item_id: int, title: str, icon_custom_emoji_id: Optional[str] = None
) -> None:
    async with session_maker() as s:
        await s.execute(
            update(MenuItem)
            .where(MenuItem.id == item_id)
            .values(title=title, icon_custom_emoji_id=icon_custom_emoji_id)
        )
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
                .order_by(Content.id)
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


async def get_sub_check_button() -> dict[str, Optional[str]]:
    """Majburiy obunadagi tekshirish tugmasining matni va premium ikonkasini beradi."""
    keys = (K_SUB_CHECK_TEXT, K_SUB_CHECK_ICON)
    async with session_maker() as s:
        rows = await s.execute(
            select(Setting.key, Setting.value).where(Setting.key.in_(keys))
        )
        values = {key: value for key, value in rows}
    return {
        "text": values.get(K_SUB_CHECK_TEXT) or DEFAULT_SUB_CHECK_TEXT,
        "icon_custom_emoji_id": values.get(K_SUB_CHECK_ICON),
    }


async def set_sub_check_button(
    text: str, icon_custom_emoji_id: Optional[str] = None
) -> None:
    value = text.strip()
    if not value or len(value) > 64:
        raise ValueError("Tugma matni 1–64 ta belgi bo'lishi kerak")
    await set_setting(K_SUB_CHECK_TEXT, value)
    await set_setting(K_SUB_CHECK_ICON, icon_custom_emoji_id)


async def reset_sub_check_button() -> None:
    await set_setting(K_SUB_CHECK_TEXT, None)
    await set_setting(K_SUB_CHECK_ICON, None)


async def is_force_sub_on_start_enabled() -> bool:
    """A'zo bo'lsa ham har `/start` da obuna ekranini ko'rsatish sozlamasi."""
    return (await get_setting(K_FORCE_SUB_ON_START, "0")) == "1"


async def toggle_force_sub_on_start() -> bool:
    enabled = not await is_force_sub_on_start_enabled()
    await set_setting(K_FORCE_SUB_ON_START, "1" if enabled else "0")
    return enabled


async def get_ref_text() -> Optional[str]:
    """Admin qo'ygan taklif matni. Qo'yilmagan bo'lsa None (standart ishlatiladi)."""
    return await get_setting(K_REF_TEXT)


async def set_ref_text(text_html: str) -> None:
    await set_setting(K_REF_TEXT, text_html)


async def delete_ref_text() -> None:
    """Standart matnga qaytaradi."""
    await set_setting(K_REF_TEXT, None)


async def get_my_points_settings() -> dict[str, object]:
    """Asosiy menyudagi "Ballarim" tugmasi sozlamalari."""
    keys = (
        K_MY_POINTS_ENABLED,
        K_MY_POINTS_TEXT,
        K_MY_POINTS_STYLE,
        K_MY_POINTS_ICON,
        K_MY_POINTS_MESSAGE,
    )
    async with session_maker() as s:
        rows = await s.execute(
            select(Setting.key, Setting.value).where(Setting.key.in_(keys))
        )
        values = {key: value for key, value in rows}

    style = values.get(K_MY_POINTS_STYLE)
    if style not in BUTTON_STYLES:
        style = None
    return {
        "enabled": values.get(K_MY_POINTS_ENABLED, "1") != "0",
        "text": values.get(K_MY_POINTS_TEXT) or DEFAULT_MY_POINTS_TEXT,
        "style": style,
        "icon_custom_emoji_id": values.get(K_MY_POINTS_ICON),
        "message": values.get(K_MY_POINTS_MESSAGE),
    }


async def set_my_points_enabled(enabled: bool) -> None:
    await set_setting(K_MY_POINTS_ENABLED, "1" if enabled else "0")


async def set_my_points_text(
    text: str, icon_custom_emoji_id: Optional[str] = None
) -> None:
    value = text.strip()
    if not value or len(value) > 64:
        raise ValueError("Tugma matni 1–64 ta belgi bo'lishi kerak")
    await set_setting(K_MY_POINTS_TEXT, value)
    await set_setting(K_MY_POINTS_ICON, icon_custom_emoji_id)


async def set_my_points_style(style: Optional[str]) -> None:
    if style is not None and style not in BUTTON_STYLES:
        raise ValueError(f"Noto'g'ri tugma uslubi: {style}")
    await set_setting(K_MY_POINTS_STYLE, style)


async def set_my_points_message(text_html: str) -> None:
    await set_setting(K_MY_POINTS_MESSAGE, text_html)


async def delete_my_points_message() -> None:
    await set_setting(K_MY_POINTS_MESSAGE, None)


async def get_rating_settings() -> dict[str, object]:
    """Asosiy menyudagi reyting tugmasi va posti sozlamalari."""
    keys = (
        K_RATING_ENABLED,
        K_RATING_TEXT,
        K_RATING_STYLE,
        K_RATING_ICON,
        K_RATING_MESSAGE,
        K_RATING_ROW_SIZE,
    )
    async with session_maker() as s:
        rows = await s.execute(
            select(Setting.key, Setting.value).where(Setting.key.in_(keys))
        )
        values = {key: value for key, value in rows}

    style = values.get(K_RATING_STYLE)
    if style not in BUTTON_STYLES:
        style = None
    try:
        row_size = int(values.get(K_RATING_ROW_SIZE) or "2")
    except ValueError:
        row_size = 2
    if row_size not in {1, 2, 3, 4}:
        row_size = 2
    return {
        "enabled": values.get(K_RATING_ENABLED, "1") != "0",
        "text": values.get(K_RATING_TEXT) or DEFAULT_RATING_TEXT,
        "style": style,
        "icon_custom_emoji_id": values.get(K_RATING_ICON),
        "message": values.get(K_RATING_MESSAGE),
        "row_size": row_size,
    }


async def set_rating_enabled(enabled: bool) -> None:
    await set_setting(K_RATING_ENABLED, "1" if enabled else "0")


async def set_rating_text(
    text: str, icon_custom_emoji_id: Optional[str] = None
) -> None:
    value = text.strip()
    if not value or len(value) > 64:
        raise ValueError("Tugma matni 1–64 ta belgi bo'lishi kerak")
    await set_setting(K_RATING_TEXT, value)
    await set_setting(K_RATING_ICON, icon_custom_emoji_id)


async def set_rating_style(style: Optional[str]) -> None:
    if style is not None and style not in BUTTON_STYLES:
        raise ValueError(f"Noto'g'ri tugma uslubi: {style}")
    await set_setting(K_RATING_STYLE, style)


async def set_rating_message(text_html: str) -> None:
    await set_setting(K_RATING_MESSAGE, text_html)


async def delete_rating_message() -> None:
    await set_setting(K_RATING_MESSAGE, None)


async def set_rating_row_size(row_size: int) -> None:
    if row_size not in {1, 2, 3, 4}:
        raise ValueError(f"Noto'g'ri qator o'lchami: {row_size}")
    await set_setting(K_RATING_ROW_SIZE, str(row_size))


async def get_winners_limit() -> int:
    """Bitta Telegram xabarida ko'rsatiladigan g'oliblar soni."""
    try:
        value = int(await get_setting(K_WINNERS_LIMIT, str(DEFAULT_WINNERS_LIMIT)) or "")
    except ValueError:
        value = DEFAULT_WINNERS_LIMIT
    return min(max(value, 1), MAX_WINNERS_LIMIT)


async def set_winners_limit(limit: int) -> None:
    if not 1 <= limit <= MAX_WINNERS_LIMIT:
        raise ValueError(
            f"G'oliblar soni 1..{MAX_WINNERS_LIMIT} oralig'ida bo'lishi kerak"
        )
    await set_setting(K_WINNERS_LIMIT, str(limit))


async def is_phone_required() -> bool:
    return (await get_setting(K_ASK_PHONE, "0")) == "1"


async def toggle_phone_required() -> bool:
    new = not await is_phone_required()
    await set_setting(K_ASK_PHONE, "1" if new else "0")
    return new


# ================================================================ YOPIQ KANAL LINKI
async def get_private_link_settings() -> dict:
    """Yopiq kanal linki sozlamalari.

    `post` — admin qo'ygan post (send_raw_content formatida) yoki None (standart).
    """
    keys = (
        K_PL_ENABLED,
        K_PL_CHAT_ID,
        K_PL_CHAT_TITLE,
        K_PL_NEED,
        K_PL_TYPE,
        K_PL_FILE,
        K_PL_TEXT,
        K_PL_BUTTON_TEXT,
        K_PL_BUTTON_ICON,
    )
    async with session_maker() as s:
        rows = await s.execute(
            select(Setting.key, Setting.value).where(Setting.key.in_(keys))
        )
        values = {key: value for key, value in rows}

    raw_chat_id = (values.get(K_PL_CHAT_ID) or "").strip()
    chat_id = int(raw_chat_id) if raw_chat_id.lstrip("-").isdigit() else None
    raw_need = (values.get(K_PL_NEED) or "").strip()
    need = int(raw_need) if raw_need.isdigit() else 0
    post_type = values.get(K_PL_TYPE)
    post = (
        {
            "type": post_type,
            "file_id": values.get(K_PL_FILE),
            "text_html": values.get(K_PL_TEXT) or "",
        }
        if post_type
        else None
    )
    return {
        "enabled": values.get(K_PL_ENABLED) == "1",
        "chat_id": chat_id,
        "chat_title": values.get(K_PL_CHAT_TITLE) or "",
        "need": need,
        "post": post,
        # None -> standart "🔐 Kanalga kirish" (utils.private_link.BTN_JOIN)
        "button_text": values.get(K_PL_BUTTON_TEXT),
        "button_icon": values.get(K_PL_BUTTON_ICON),
    }


async def set_private_link_enabled(enabled: bool) -> None:
    await set_setting(K_PL_ENABLED, "1" if enabled else "0")


async def set_private_link_channel(chat_id: int, title: str) -> None:
    await set_setting(K_PL_CHAT_ID, str(chat_id))
    await set_setting(K_PL_CHAT_TITLE, title)


async def set_private_link_need(need: int) -> None:
    if need < 1:
        raise ValueError("Takliflar soni kamida 1 bo'lishi kerak")
    await set_setting(K_PL_NEED, str(need))


async def set_private_link_post(
    type_: str, file_id: Optional[str], text_html: Optional[str]
) -> None:
    await set_setting(K_PL_TYPE, type_)
    await set_setting(K_PL_FILE, file_id)
    await set_setting(K_PL_TEXT, text_html)


async def set_private_link_button(text: str, icon_custom_emoji_id: Optional[str]) -> None:
    value = text.strip()
    if not value or len(value) > 64:
        raise ValueError("Tugma matni 1–64 ta belgi bo'lishi kerak")
    await set_setting(K_PL_BUTTON_TEXT, value)
    await set_setting(K_PL_BUTTON_ICON, icon_custom_emoji_id)


async def delete_private_link_button() -> None:
    """Standart "🔐 Kanalga kirish" tugmasiga qaytaradi."""
    await set_setting(K_PL_BUTTON_TEXT, None)
    await set_setting(K_PL_BUTTON_ICON, None)


async def delete_private_link_post() -> None:
    """Standart postga qaytaradi."""
    for key in (K_PL_TYPE, K_PL_FILE, K_PL_TEXT):
        await set_setting(key, None)


async def get_private_link_grant(
    user_tg_id: int, chat_id: int
) -> Optional[PrivateLinkGrant]:
    async with session_maker() as s:
        return await s.scalar(
            select(PrivateLinkGrant).where(
                PrivateLinkGrant.user_tg_id == user_tg_id,
                PrivateLinkGrant.chat_id == chat_id,
            )
        )


async def add_private_link_grant(user_tg_id: int, chat_id: int, invite_link: str) -> None:
    async with session_maker() as s:
        stmt = (
            pg_insert(PrivateLinkGrant)
            .values(user_tg_id=user_tg_id, chat_id=chat_id, invite_link=invite_link)
            .on_conflict_do_nothing(constraint="uq_private_link_grant")
        )
        await s.execute(stmt)
        await s.commit()


async def count_private_link_grants(chat_id: int) -> int:
    async with session_maker() as s:
        return await s.scalar(
            select(func.count(PrivateLinkGrant.id)).where(
                PrivateLinkGrant.chat_id == chat_id
            )
        ) or 0


async def get_ref_notify_text() -> Optional[str]:
    """Admin qo'ygan tabrik matni. Qo'yilmagan bo'lsa None (standart ishlatiladi)."""
    return await get_setting(K_REF_NOTIFY_TEXT)


async def set_ref_notify_text(text_html: str) -> None:
    await set_setting(K_REF_NOTIFY_TEXT, text_html)


async def delete_ref_notify_text() -> None:
    await set_setting(K_REF_NOTIFY_TEXT, None)

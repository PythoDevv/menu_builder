"""Admin o'zgartirishi mumkin bo'lgan matnlarning standart (default) qiymatlari."""

#: Majburiy obuna ekranidagi standart xabar. Admin paneldan almashtiriladi.
DEFAULT_SUB_TEXT = (
    "👋 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling.\n\n"
    "So'ng <b>✅ Tekshirish</b> tugmasini bosing."
)

#: send_raw_content() kutadigan ko'rinish — obuna xabari qo'yilmaganda ishlatiladi
DEFAULT_SUB_MESSAGE = {
    "type": "text",
    "file_id": None,
    "text_html": DEFAULT_SUB_TEXT,
}

#: Taklif shartli tugma bosilganda chiqadigan standart matn.
#: Admin paneldagi "👥 Taklif matni" bo'limidan almashtiriladi.
DEFAULT_REF_TEXT = (
    "🔒 <b>{title}</b> — bu bo'lim hozircha yopiq.\n\n"
    "Ochish uchun botga <b>{need}</b> ta do'stingizni taklif qilishingiz kerak.\n\n"
    "👥 Siz taklif qilgansiz: <b>{count}</b> ta\n"
    "⏳ Yana kerak: <b>{left}</b> ta\n\n"
    "👇 Sizning shaxsiy havolangiz:\n"
    "{link}\n\n"
    "Havolani do'stlaringizga yuboring — ular shu havola orqali botga kirsa, "
    "taklif avtomatik hisoblanadi."
)

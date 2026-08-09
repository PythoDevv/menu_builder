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

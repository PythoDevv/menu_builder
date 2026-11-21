"""Admin o'zgartirishi mumkin bo'lgan matnlarning standart (default) qiymatlari."""

#: Majburiy obuna ekranidagi standart xabar. Admin paneldan almashtiriladi.
DEFAULT_SUB_TEXT = (
    "👋 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling.\n\n"
    "So'ng <b>✅ A'zo bo'ldim</b> tugmasini bosing."
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

#: "Ballarim" tugmasi bosilganda chiqadigan standart matn.
#: Admin paneldagi "🏆 Ballarim tugmasi" bo'limidan almashtiriladi.
DEFAULT_MY_POINTS_MESSAGE = (
    "🏆 <b>Ballaringiz</b>\n\n"
    "Siz taklif qilgan odamlar soni: <b>{count}</b> ta\n\n"
    "Do'stlaringizni shu havola orqali taklif qiling:\n"
    "{link}"
)

#: "Reyting" tugmasi bosilganda chiqadigan standart post.
#: ``{users-N}`` N ta eng ko'p taklif qilgan foydalanuvchini chiqaradi.
DEFAULT_RATING_MESSAGE = (
    "🏅 <b>Takliflar reytingi</b>\n\n"
    "{users-10}\n\n"
    "Eng faol ishtirokchilar ro'yxati."
)

#: Har bir yangi taklifda taklif qilgan odamga boradigan tabrik.
#: Admin paneldagi "🔐 Yopiq kanal linki" -> "🎉 Tabrik xabari" dan almashtiriladi.
#: `{need}` yoki `{left}` bor qator faqat yopiq kanal maqsadi faol bo'lganda chiqadi.
DEFAULT_REF_NOTIFY_TEXT = (
    "🎉 <b>Tabriklaymiz!</b>\n\n"
    "Sizning havolangiz orqali <b>{name}</b> botga qo'shildi.\n"
    "➕ Sizga <b>+1 ball</b> berildi.\n\n"
    "🏆 Jami ballaringiz: <b>{count}</b> ta\n"
    "🔐 Yopiq kanal linkigacha yana <b>{left}</b> ta taklif qoldi."
)

#: Taklif sharti bajarilganda yuboriladigan post (admin qo'ymagan bo'lsa).
DEFAULT_PRIVATE_LINK_TEXT = (
    "🎉 <b>Tabriklaymiz!</b>\n\n"
    "Siz <b>{count}</b> ta do'stingizni taklif qildingiz va yopiq kanalga "
    "kirish huquqini qo'lga kiritdingiz.\n\n"
    "🔐 Sizning shaxsiy havolangiz:\n"
    "{link}\n\n"
    "⚠️ Havola faqat siz uchun va bir marta ishlaydi — uni boshqalarga bermang."
)

#: "Konkursda qatnashish" tugmasi bosilganda keladigan tarqatish posti.
#: Foydalanuvchi uni do'stlariga / guruhlarga forward qiladi. `{link}` o'rniga
#: o'sha odamning shaxsiy taklif havolasi (`...?start=ref<tg_id>`) qo'yiladi.
#: Admin paneldagi "🎁 Konkurs tugmasi" -> "📝 Tarqatish posti" dan almashtiriladi.
DEFAULT_CONTEST_POST_TEXT = (
    "🎁 <b>Katta konkurs boshlandi!</b>\n\n"
    "Botga qo'shiling, do'stlaringizni taklif qiling va qimmatbaho sovg'alarni "
    "yutib oling 🏆\n\n"
    "✅ Qatnashish bepul — bor-yo'g'i bir necha soniya.\n\n"
    "👇 Qatnashish uchun havola:\n"
    "{link}"
)

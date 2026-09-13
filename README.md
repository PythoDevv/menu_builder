# Menu Builder Bot

Admin panelidan boshqariladigan menyu-bot. aiogram 3 + PostgreSQL + SQLAlchemy, polling rejimida.

Menyu va admin panel tugmalari — **reply (pastdagi) klaviatura**. Faqat majburiy obuna
ekrani **inline**, chunki reply tugmaga kanal havolasini (URL) qo'yib bo'lmaydi.

## Imkoniyatlar

- **Adminlar** — paneldan telegram ID raqami orqali qo'shiladi/o'chiriladi. `.env` dagilar asosiy admin bo'lib qoladi.
- **Obuna tekshiruvi** — ochiq va yopiq (qo'shilish so'rovi) kanallar. Zayafka tashlagan odamdan qayta so'ralmaydi.
- **Obuna xabari** — majburiy obuna ekranidagi post admin paneldan almashtiriladi: matn, rasm, video, fayl (`file_id` bilan). Qo'yilmagan bo'lsa standart matn chiqadi. Kanal tugmalari va **✅ Tekshirish** xabar ostiga avtomatik qo'shiladi.
- **Start xabar** — admin paneldan qo'shiladi / o'zgartiriladi / o'chiriladi. Qo'yilmagan bo'lsa ko'rsatilmaydi.
- **Menyu tugmalari** — cheksiz darajali daraxt. Har bir tugmaga kontent (rasm/video/fayl/matn) biriktiriladi.
- **Menyu ko'rinishi** — tugmalar qatorda **bittadan** yoki **ikkitadan** chiqishi admin paneldan tanlanadi. Ikkitadan rejimida nomi uzun tugma qatorni o'zi egallaydi (matni siqilib ketmaydi).
- **Kontent** — `file_id` + HTML holida saqlanadi, foydalanuvchiga o'sha holicha yuboriladi (qayta yuklanmaydi).
- **Taklif (referal) sharti** — tugma faqat N ta odam taklif qilgandan keyin ochiladi. Shart tugma qo'shilayotganda so'raladi, keyin ham o'zgartiriladi. Shart bajarilmaganda chiqadigan matn admin paneldan sozlanadi.
- **Telefon so'rash** — admin paneldan yoqiladi/o'chiriladi. Bir marta olingan raqam qayta so'ralmaydi.
- **Hammaga xabar** — bloklaganlar avtomatik belgilanadi.
- **Excel** — `exports/users.xlsx`, har kuni cron bilan yangilanadi (yangi fayl ochilmaydi).

## O'rnatish

```bash
cd /home/ilyos/private_bots/menu_builder

# 1) Bazani yaratish
psql -U postgres -c "CREATE DATABASE menu_builder_db"

# 2) venv (allaqachon yaratilgan bo'lsa o'tkazib yuboring)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3) .env ni to'ldirish: BOT_TOKEN, ADMINS, DB_URL

# 4) Ishga tushirish
python main.py
```

Jadvallar birinchi ishga tushishda avtomatik yaratiladi.

## Root menyuni JSON'dan yuklash

`data/root_menu.json` asosiy menyu tugmalari va ularning tartibini saqlaydi.
Importer mavjud tugmalarni nomi/aliasi orqali topadi, yo'q tugmalarni yaratadi va
ro'yxatda ko'rsatilmagan mavjud root tugmalarni oxiriga o'tkazadi. Ichki tugmalar va
kontent o'chirilmaydi.

Serverda avval natijani yozmasdan ko'ring, keyin bazaga qo'llang:

```bash
cd /root/menu_builder
source venv/bin/activate
python scripts/import_root_menu.py
python scripts/import_root_menu.py --apply
```

Importer `.env` dagi `DB_URL` bazasidan foydalanadi. Bot tokeni bu jarayon uchun
kerak emas. Bot ishlab turgan bo'lsa ham, keyingi ochilgan menyuda yangi tartib
avtomatik ko'rinadi.

## Dars submenyularini yuklash

`data/lesson_menu.json` ichidagi submenyular videoni bazaga yoki serverga
yuklamaydi. Har bir kontent uchun manba kanalning `chat_id` va eksport HTML'idagi
`message_id` saqlanadi; foydalanuvchi tugmani bosganda bot Telegram'ning
`copyMessage` metodi bilan xabarni nusxalaydi.

Default dataset `ChatExport_2026-09-13` asosida tuzilgan: 12 ta asosiy menyu,
401 ta noyob video va 61 ta PDF/hujjat. Kanalda takrorlangan bitta video xabari
(`message_id=201`) qayta yuborilmasligi uchun ro'yxatga kiritilmagan.

Bot manba kanal/guruhda a'zo bo'lishi, protected content o'chirilgan bo'lishi kerak.
`.env` ga `SOURCE_CHAT_ID=-100...` kiriting. So'ng serverda:

```bash
python migrate.py
python scripts/import_root_menu.py --apply
python scripts/import_lesson_menu.py          # dry run
python scripts/import_lesson_menu.py --apply
supervisorctl restart menu_builder_bot
```

To'liq HTML eksportdan JSON'ni qayta yaratish kerak bo'lsa:

```bash
python scripts/build_lesson_menu_data.py /path/to/ChatExport_2026-09-13
```

## Migratsiya (serverda yangilash)

Bazada allaqachon ma'lumot bor bo'lsa, yangilashdan keyin migratsiyani qo'llash kerak:

```bash
cd /root/menu_builder            # serverdagi papka
git pull
source venv/bin/activate
pip install -r requirements.txt
python migrate.py                # yangi jadvallarni qo'shadi
supervisorctl restart menu_builder_bot
```

`migrate.py` qaysi fayl qo'llanganini `schema_migrations` jadvalida saqlaydi —
qayta ishga tushirsangiz bajarilgani takrorlanmaydi.

Yangi migratsiya qo'shish uchun `migrations/` ichiga `002_...sql` ko'rinishida
fayl tashlang (nomi bo'yicha tartib bilan bajariladi).

## Admin panel

`/admin` — `.env` dagi `ADMINS` va paneldan qo'shilgan adminlar uchun.
Paneldan chiqish — **🚪 Chiqish** (yoki `/start`), shundan keyin admin ham
oddiy foydalanuvchi menyusini ko'radi.

| Bo'lim | Nima qiladi |
|---|---|
| 👮 Adminlar | ID raqami orqali admin qo'shish / adminlikdan olish |
| 📢 Kanallar | Qo'shish / o'chirish / yoqish-o'chirish. Bot kanalda **admin** bo'lishi shart. |
| 🆕 Avtomatik so'rov | Bot kanalga admin qilinsa, **admin qilgan odamning o'ziga** "qo'shilsinmi?" so'rovi keladi (pastda) |
| 🗂 Menyu tugmalari | Tugma qo'shish, nomini o'zgartirish, tartiblash, yashirish, o'chirish, kontent biriktirish, **taklif sharti** |
| ✏️ Start xabar | Ko'rish / o'zgartirish / o'chirish |
| 📌 Obuna xabari | Majburiy obuna postini qo'yish (matn/rasm/video), ko'rish, standartga qaytarish |
| ✍️ Taklif matni | Taklif sharti bajarilmaganda chiqadigan matn: ko'rish, o'zgartirish, standartga qaytarish |
| ☎️ Telefon so'rash | ON / OFF |
| 🧩 Menyu ko'rinishi | Tugmalar 1 tadan yoki 2 tadan chiqishi + namunani ko'rish |
| 📨 Xabar yuborish | Hamma faol foydalanuvchiga |
| 📊 Excel | Faylni olish yoki qo'lda yangilash |
| 👥 Statistika | Jami / faol / bugun / 7 kun |

## Taklif (referal) sharti

Tugmani "yopiq" qilib qo'yish mumkin: foydalanuvchi belgilangan sonda odam taklif
qilmaguncha tugma ichidagi kontent (yoki ichki bo'lim) ochilmaydi.

**Yangi tugma qo'shganda** bot nomini so'ragandan keyin: *"Bu tugma odam taklif
qilgandan keyin ochilsinmi?"* — **✅ Ha** / **❌ Yo'q**.

- **❌ Yo'q** — son umuman so'ralmaydi, tugma hammaga ochiq (`required_referrals = 0`).
- **✅ Ha** — necha kishi kerakligi so'raladi. Faqat **0 dan katta** butun son qabul
  qilinadi (1 … 10000). `0`, manfiy son yoki harf yozilsa saqlanmaydi va qayta so'raladi.

**Keyin o'zgartirish**: 🗂 Menyu tugmalari → tugmaning ichiga kiring →
**👥 Taklif sharti** → ➕ Qo'shish / ✏️ O'zgartirish / 🚫 Shartni olib tashlash.
Ro'yxatda shartli tugmalar `🔒5` belgisi bilan ko'rinadi.

**Foydalanuvchi tomonida**: shartli tugma bosilganda kontent o'rniga
**✍️ Taklif matni** bo'limidagi matn va uning shaxsiy havolasi chiqadi
(ostida **📤 Do'stlarga yuborish** tugmasi bilan). Talab bajarilgach tugma
o'z-o'zidan ochiladi — hech narsani qayta bosish shart emas.

Bundan tashqari, asosiy menyu tagida doimiy **🏆 Ballarim** tugmasi bor —
hech qanday shartli tugmaga bog'liq bo'lmasdan, istalgan vaqtda taklif
qilinganlar sonini va shaxsiy havolani ko'rsatadi.

Matnda ishlatiladigan o'rinbosarlar:

| Belgi | Ma'nosi |
|---|---|
| `{title}` | tugma nomi |
| `{need}` | kerakli taklif soni |
| `{count}` | foydalanuvchi taklif qilgan son |
| `{left}` | yana nechta kerak |
| `{link}` | foydalanuvchining shaxsiy havolasi |

`{link}` yozilmasa, havola xabar oxiriga avtomatik qo'shiladi.

**Qanday sanaladi**

- Havola: `https://t.me/<bot>?start=ref<tg_id>`.
- Taklif **faqat yangi odam** botga birinchi marta kirganda hisoblanadi. Botda
  allaqachon bor odam boshqa havoladan kirsa — qayta hisoblanmaydi.
- O'zini o'zi taklif qilish va botda bo'lmagan ID ishlamaydi.
- Payload obuna/telefon tekshiruvidan **oldin** o'qiladi, shuning uchun foydalanuvchi
  avval kanalga obuna bo'lishi kerak bo'lsa ham taklif yo'qolmaydi. Odam
  `/start` bosishi bilan sanaladi (obunani kutmaydi).
- Taklif qilgan odamga darhol xabar boradi: *"🎉 Yangi taklif! Jami: N ta"*.
- Adminlar uchun shart tekshirilmaydi — ular tugmani doim ocha oladi. Foydalanuvchi
  nimani ko'rishini **✍️ Taklif matni → 👁 Ko'rish** orqali tekshirish mumkin.
- Kim nechta odam taklif qilgani: **👥 Statistika** (umumiy son + eng faol 5 kishi)
  va **📊 Excel** (`Takliflari` / `Kim taklif qilgan` ustunlari).

## Kanalni avtomatik qo'shish

Bot biror kanalga **admin** qilinganda `my_chat_member` keladi va bot shu zahoti
so'rov yuboradi: *"Bot falon kanalda admin qilindi. Majburiy obuna ro'yxatiga
qo'shilsinmi?"* — **✅ Ha** / **❌ Yo'q** tugmalari bilan.

- So'rov **faqat botni admin qilgan odamga** boradi va u ham **tasdiqlangan admin**
  (`.env` dagi `ADMINS` yoki paneldan qo'shilgan) bo'lsagina. Boshqa adminlarga
  hech narsa yuborilmaydi. Admin bo'lmagan odam botni kanalga qo'shsa — hech kimga
  bildirishnoma ketmaydi.
- Tasdiqlansa kanal turi **avtomatik** aniqlanadi: `@username` bor bo'lsa — 📢 ochiq,
  bo'lmasa — 🔒 yopiq (zayafkali havola o'sha yerda ochiladi).
- Kanal ro'yxatda allaqachon bo'lsa yoki botning huquqlari o'zgargan bo'lsa
  (admin → admin), so'rov qayta yuborilmaydi.
- Tugmani faqat admin bosa oladi; bosilgandan keyin bot kanalda hali ham admin
  ekanligi qayta tekshiriladi.
- Turi noto'g'ri aniqlangan bo'lsa: 📢 Kanallar → kanalni o'chirib, qo'lda qo'shing.

## Muhim

- Kanal qo'shishdan oldin botni o'sha kanalga **admin** qiling (yopiq kanalda "Invite Users via Link" huquqi ham kerak — zayafkali havola shu orqali yaratiladi).
- Yopiq kanalda so'rovni ushlash uchun bot admin bo'lishi shart, aks holda `chat_join_request` kelmaydi.
- Obuna xabari `settings` jadvalida `sub_type` / `sub_file_id` / `sub_text` kalitlarida
  saqlanadi — media `file_id` bilan, matn esa HTML formatlashi bilan. Foydalanuvchiga
  admin qanday yuborgan bo'lsa, o'sha holicha ko'rsatiladi.
- Taklif matni `settings` jadvalidagi `ref_text` kalitida turadi; taklif soni
  `menu_items.required_referrals`, kim kimni taklif qilgani `users.referred_by`
  ustunida. Eski bazada bu ustunlar `python migrate.py` (002) bilan qo'shiladi.
- Menyu ko'rinishi `settings` jadvalida `menu_columns` kalitida saqlanadi (`1` yoki `2`,
  standart — `2`). Yangi migratsiya kerak emas. Juftlash chegarasi —
  `keyboards/user_kb.py` dagi `SHORT_TITLE` (emoji ikki belgi hisoblanadi).
- Admin qaysi ekranda turgani FSM holatida saqlanadi (xotirada). Bot qayta ishga
  tushsa panel bosh sahifadan boshlanadi — `/admin` bosilsa kifoya.

## Struktura

```
main.py            — polling, middleware va routerlarni ulash
migrate.py         — SQL migratsiyalarni qo'llash
config.py          — .env sozlamalari
db/                — modellar va barcha so'rovlar
migrations/        — .sql migratsiyalar
handlers/          — foydalanuvchi va admin handlerlari
keyboards/         — reply tugmalar (+ obuna ekrani uchun inline)
middlewares/       — foydalanuvchini yozish (+ taklif payloadi), obuna va telefon tekshiruvi
utils/             — kontent, kanal, obuna, taklif logikasi, standart matnlar, excel, cron
exports/users.xlsx — kunlik yangilanadigan fayl
```

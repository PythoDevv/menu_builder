# Menu Builder Bot

Admin panelidan boshqariladigan menyu-bot. aiogram 3 + PostgreSQL + SQLAlchemy, polling rejimida.

Menyu va admin panel tugmalari — **reply (pastdagi) klaviatura**. Faqat majburiy obuna
ekrani **inline**, chunki reply tugmaga kanal havolasini (URL) qo'yib bo'lmaydi.

## Imkoniyatlar

- **Adminlar** — paneldan telegram ID raqami orqali qo'shiladi/o'chiriladi. `.env` dagilar asosiy admin bo'lib qoladi.
- **Obuna tekshiruvi** — har bir `/start` da ochiq va yopiq kanallar ko'rsatiladi; foydalanuvchi oldindan a'zo bo'lsa ham menyu faqat **A'zo bo'ldim** tugmasidan keyin ochiladi. Yopiq kanalga zayafka tashlash tekshiruvdan o'tish uchun yetarli.
- **Obuna xabari** — majburiy obuna ekranidagi post admin paneldan almashtiriladi: matn, rasm, video, fayl (`file_id` bilan). Matn/captiondagi premium custom emojilar saqlanadi. Kanal tugmalari va matni o'zgaradigan **A'zo bo'ldim** tugmasi xabar ostiga avtomatik qo'shiladi; ikkala turdagi tugmaga ham premium emoji ikonka qo'yish mumkin.
- **Start xabar** — admin paneldan qo'shiladi / o'zgartiriladi / o'chiriladi. Qo'yilmagan bo'lsa ko'rsatilmaydi.
- **Menyu tugmalari** — cheksiz darajali daraxt. Har bir tugmaga premium custom emoji ikonka va kontent (rasm/video/fayl/matn) biriktiriladi.
- **Menyu ko'rinishi** — yangi tugmalar standart **2 talik** yaratiladi; keyin har birini **1, 2, 3 yoki 4 talik** qilib sozlash mumkin. Ketma-ket bir xil turdagi tugmalar bitta qatorga guruhlanadi.
- **Kontent** — `file_id` + Telegram entitylari holida saqlanadi, foydalanuvchiga o'sha holicha yuboriladi (qayta yuklanmaydi). Premium custom emoji ID si ham yo'qolmaydi. Oddiy va premium stikerlar ham qo'llanadi.
- **Tugma rangi** — har bir menyu tugmasi uchun oddiy, ko'k, yashil yoki qizil Telegram uslubini tanlash mumkin.
- **Ballarim tugmasi** — admin paneldan ko'rsatish/yashirish, nomi, rangi va bosilganda chiqadigan xabarni o'zgartirish mumkin. Tugma ikonkasida va xabarda premium custom emoji saqlanadi.
- **Reyting tugmasi** — ko'rsatish/yashirish, nomi, premium emoji ikonka, rangi va 1–4 talik joylashuvi boshqariladi. Reyting posti formatlash/premium emojilarni saqlaydi; `{users-10}` kabi kalit top foydalanuvchilarni chiqaradi.
- **G'oliblar** — admin 1–20 oralig'ida natija sonini belgilaydi; tanlangan TOP foydalanuvchilarning ism, username, Telegram ID va ballari bitta xabarda chiqadi. Alohida ID bo'yicha xabar bo'limidan botdagi istalgan odamga matn/media/fayl yuboriladi.
- **Superadmin** — faqat `.env` dagi `ADMINS` uchun `/superadmin`: dump olib ballarni nolga tushirish va raqamlangan dumpni tanlab bazani qayta tiklash.
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

## Migratsiya (serverda yangilash)

Bazada allaqachon ma'lumot bor bo'lsa, yangilashdan keyin migratsiyani qo'llash kerak:

```bash
cd /root/menu_builder            # serverdagi papka
git pull
source venv/bin/activate
pip install -r requirements.txt
python migrate.py                # avval dump oladi, keyin migratsiyani qo'llaydi
supervisorctl restart menu_builder_bot
```

`migrate.py` qaysi fayl qo'llanganini `schema_migrations` jadvalida saqlaydi —
qayta ishga tushirsangiz bajarilgani takrorlanmaydi.

`migrate.py` har ishga tushganda, SQL ishlashidan **oldin** baza `dumps/` papkasiga
`backup_0001_YYYYMMDD_HHMMSS_pre_migrate.dump` ko'rinishida saqlanadi. `pg_dump`
muvaffaqiyatsiz tugasa migratsiya umuman boshlanmaydi. Yangi migratsiya bo'lmasa
ham dump yaratiladi, SQL esa qayta bajarilmaydi. Serverda PostgreSQL client
(`pg_dump`, `pg_restore`) o'rnatilgan bo'lishi kerak.

Dumpni qayta tiklash:

```bash
supervisorctl stop menu_builder_bot
python3 restore.py
supervisorctl start menu_builder_bot
```

`restore.py` raqamlangan dumplarni eng yangisidan boshlab ko'rsatadi (Enter bosilsa
oxirgisi tanlanadi). Tanlangan dump yozilishidan oldin bazaning joriy holati ham
`pre_restore` nomi bilan avtomatik dump qilinadi. Yakuniy tasdiq uchun `RESTORE`
so'zini yozish kerak.

Yangi migratsiya qo'shish uchun `migrations/` ichiga `002_...sql` ko'rinishida
fayl tashlang (nomi bo'yicha tartib bilan bajariladi).

## Admin panel

`/admin` — `.env` dagi `ADMINS` va paneldan qo'shilgan adminlar uchun.
Paneldan chiqish — **🚪 Chiqish** (yoki `/start`), shundan keyin admin ham
oddiy foydalanuvchi menyusini ko'radi.

| Bo'lim | Nima qiladi |
|---|---|
| 👮 Adminlar | ID raqami orqali admin qo'shish / adminlikdan olish |
| 📢 Kanallar | Qo'shish / o'chirish / yoqish-o'chirish va obuna tugmasiga premium emoji qo'yish. Bot kanalda **admin** bo'lishi shart. |
| 🆕 Avtomatik so'rov | Bot kanalga admin qilinsa, **admin qilgan odamning o'ziga** "qo'shilsinmi?" so'rovi keladi (pastda) |
| 🗂 Menyu tugmalari | Tugma qo'shish, nomini/rangini va **1–4 talik ko'rinishini** o'zgartirish, tartiblash, yashirish, o'chirish, kontent biriktirish, **taklif sharti** |
| ✏️ Start xabar | Ko'rish / o'zgartirish / o'chirish |
| 📌 Obuna xabari | Majburiy obuna postini premium emojilari bilan qo'yish, ko'rish, standartga qaytarish va **Tekshirish** tugmasi matni/premium emojisini sozlash |
| ✍️ Taklif matni | Taklif sharti bajarilmaganda chiqadigan matn: ko'rish, o'zgartirish, standartga qaytarish |
| ☎️ Telefon so'rash | ON / OFF |
| 🏆 Ballarim tugmasi | Ko'rsatish/yashirish, nomi, rangi, premium emoji va natija xabarini o'zgartirish |
| 🏅 Reyting tugmasi | Ko'rsatish/yashirish, nomi, rangi, premium emoji, joylashuvi va `{users-N}` kalitli postni o'zgartirish |
| 🏆 G'oliblar | Natijalar sonini sozlash, to'liq TOP ro'yxatni bitta xabarda olish va Telegram ID bo'yicha bitta odamga xabar yuborish |
| 📨 Xabar yuborish | Hamma faol foydalanuvchiga |
| 📊 Excel | Faylni olish yoki qo'lda yangilash |
| 👥 Statistika | Jami / faol / bugun / 7 kun |

`/superadmin` Telegram komandalar ro'yxatida hech kimga ko'rinmaydi. Uni qo'lda
yozganda esa faqat `.env` dagi `ADMINS` uchun handler ishlaydi. Ballarni tozalashdan oldin
`pre_points_reset`, restore oldidan esa `pre_restore` dump avtomatik yaratiladi.

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

Bundan tashqari, asosiy menyu tagidagi **🏆 Ballarim** tugmasi hech qanday shartli
tugmaga bog'liq bo'lmasdan taklif qilinganlar sonini va shaxsiy havolani ko'rsatadi.
Admin uning ko'rinishini, matnini va Telegram ruxsat bergan rangini o'zgartira oladi.
Telegram Bot API sariq fon bermaydi; sariq urg'u kerak bo'lsa tugma matnida `🟡`
emoji ishlatish mumkin, lekin tugmaning haqiqiy foni sariq bo'lmaydi.

Ballarim xabarida `{count}` foydalanuvchining takliflari soniga, `{link}` esa uning
shaxsiy taklif havolasiga almashtiriladi. `{link}` kaliti xabarda bo'lishi shart.
Telegram ichida formatlangan premium custom emoji yuborilsa, uning
`custom_emoji_id` qiymati HTML shablon bilan birga saqlanadi. Tugma nomidagi
birinchi premium custom emoji alohida ikonka sifatida saqlanadi. Buning ishlashi
uchun bot egasining Telegram Premium obunasi faol bo'lishi kerak.

## Reyting posti

Admin panel → **🏅 Reyting tugmasi** orqali tugma va post sozlanadi. Post ichida
`{users-N}` yozilsa, shu joyga eng ko'p odam taklif qilgan N ta foydalanuvchi
joylanadi. Masalan, `{users-10}` — top 10. N qiymati 1–50 oralig'ida xavfsiz
chegaralanadi. Ro'yxatning tepasi va pastida aynan bittadan bo'sh qator avtomatik
qoldiriladi.

Post Telegram formatida saqlanadi: qalin/kursiv matn, havola va premium custom
emojilar ishlaydi. Tugma nomiga qo'shilgan birinchi premium custom emoji alohida
ikonka sifatida ishlatiladi. 2 talik joylashuvda standart holatda **Ballarim** va
**Reyting** bitta qatorda chiqadi.

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
  saqlanadi — media `file_id` bilan, matn esa Telegram entitylari (premium emoji IDlari
  bilan) holida. Foydalanuvchiga admin qanday yuborgan bo'lsa, o'sha holicha ko'rsatiladi.
- Tekshirish tugmasi `sub_check_text` / `sub_check_icon_custom_emoji_id` sozlamalarida,
  kanal tugmasining premium emojisi esa `channels.icon_custom_emoji_id` ustunida saqlanadi.
  Kanal ikonkalari uchun `006_channel_button_custom_emoji.sql` migratsiyasini qo'llash kerak.
- Taklif matni `settings` jadvalidagi `ref_text` kalitida turadi; taklif soni
  `menu_items.required_referrals`, kim kimni taklif qilgani `users.referred_by`
  ustunida. Eski bazada bu ustunlar `python migrate.py` (002) bilan qo'shiladi.
- Har bir tugmaning ko'rinishi `menu_items.row_size` ustunida saqlanadi (`1`–`4`).
  `005_menu_item_row_size.sql` migratsiyasi eski tugmalarga `1` qiymatini beradi.
  Bir xil `row_size` qiymatli ketma-ket tugmalar tanlangan songacha bitta qatorda chiqadi.
- Admin qaysi ekranda turgani FSM holatida saqlanadi (xotirada). Bot qayta ishga
  tushsa panel bosh sahifadan boshlanadi — `/admin` bosilsa kifoya.

## Struktura

```
main.py            — polling, middleware va routerlarni ulash
migrate.py         — SQL migratsiyalarni qo'llash
restore.py         — raqamlangan dumpni tanlab bazaga qayta tiklash
db_backup.py       — pg_dump/pg_restore va dump raqamlash logikasi
config.py          — .env sozlamalari
db/                — modellar va barcha so'rovlar
migrations/        — .sql migratsiyalar
handlers/          — foydalanuvchi va admin handlerlari
keyboards/         — reply tugmalar (+ obuna ekrani uchun inline)
middlewares/       — foydalanuvchini yozish (+ taklif payloadi), obuna va telefon tekshiruvi
utils/             — kontent, kanal, obuna, taklif logikasi, standart matnlar, excel, cron
exports/users.xlsx — kunlik yangilanadigan fayl
```

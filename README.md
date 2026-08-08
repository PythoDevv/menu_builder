# Menu Builder Bot

Admin panelidan boshqariladigan menyu-bot. aiogram 3 + PostgreSQL + SQLAlchemy, polling rejimida.

## Imkoniyatlar

- **Adminlar** — paneldan telegram ID raqami orqali qo'shiladi/o'chiriladi. `.env` dagilar asosiy admin bo'lib qoladi.
- **Obuna tekshiruvi** — ochiq va yopiq (qo'shilish so'rovi) kanallar. Zayafka tashlagan odamdan qayta so'ralmaydi.
- **Start xabar** — admin paneldan qo'shiladi / o'zgartiriladi / o'chiriladi. Qo'yilmagan bo'lsa ko'rsatilmaydi.
- **Menyu tugmalari** — cheksiz darajali daraxt. Har bir tugmaga kontent (rasm/video/fayl/matn) biriktiriladi.
- **Kontent** — `file_id` + HTML holida saqlanadi, foydalanuvchiga o'sha holicha yuboriladi (qayta yuklanmaydi).
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
python migrate.py                # yangi jadvallarni qo'shadi
supervisorctl restart menu_builder_bot
```

`migrate.py` qaysi fayl qo'llanganini `schema_migrations` jadvalida saqlaydi —
qayta ishga tushirsangiz bajarilgani takrorlanmaydi.

Yangi migratsiya qo'shish uchun `migrations/` ichiga `002_...sql` ko'rinishida
fayl tashlang (nomi bo'yicha tartib bilan bajariladi).

## Admin panel

`/admin` — `.env` dagi `ADMINS` va paneldan qo'shilgan adminlar uchun.

| Bo'lim | Nima qiladi |
|---|---|
| 👮 Adminlar | ID raqami orqali admin qo'shish / adminlikdan olish |
| 📢 Kanallar | Qo'shish / o'chirish / yoqish-o'chirish. Bot kanalda **admin** bo'lishi shart. |
| 🗂 Menyu tugmalari | Tugma qo'shish, nomini o'zgartirish, tartiblash, yashirish, o'chirish, kontent biriktirish |
| ✏️ Start xabar | Ko'rish / o'zgartirish / o'chirish |
| ☎️ Telefon so'rash | ON / OFF |
| 📨 Xabar yuborish | Hamma faol foydalanuvchiga |
| 📊 Excel | Faylni olish yoki qo'lda yangilash |
| 👥 Statistika | Jami / faol / bugun / 7 kun |

## Muhim

- Kanal qo'shishdan oldin botni o'sha kanalga **admin** qiling (yopiq kanalda "Invite Users via Link" huquqi ham kerak — zayafkali havola shu orqali yaratiladi).
- Yopiq kanalda so'rovni ushlash uchun bot admin bo'lishi shart, aks holda `chat_join_request` kelmaydi.

## Struktura

```
main.py            — polling, middleware va routerlarni ulash
migrate.py         — SQL migratsiyalarni qo'llash
config.py          — .env sozlamalari
db/                — modellar va barcha so'rovlar
migrations/        — .sql migratsiyalar
handlers/          — foydalanuvchi va admin handlerlari
keyboards/         — inline tugmalar
middlewares/       — foydalanuvchini yozish, obuna va telefon tekshiruvi
utils/             — kontent, obuna logikasi, excel, cron
exports/users.xlsx — kunlik yangilanadigan fayl
```

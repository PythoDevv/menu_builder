# Telegram premium sticker, custom emoji va tugma ranglari

Tekshirilgan sana: 2026-09-26. Manbalar faqat Telegram Bot API va aiogram'ning rasmiy hujjatlari.

## Qisqa xulosa

- Foydalanuvchi yuborgan **premium sticker** oddiy sticker xabari sifatida keladi. `message.sticker.file_id` saqlanib, `sendSticker(sticker=file_id)` bilan qayta yuboriladi.
- Premium stickerning `premium_animation.file_id` qiymatini emas, asosiy `message.sticker.file_id` qiymatini saqlash kerak.
- Matn ichidagi **custom emoji** sticker xabari emas. U `MessageEntity(type="custom_emoji", custom_emoji_id=...)` sifatida keladi. Uni matn ichida qayta yuborish uchun `custom_emoji_id` va custom-emoji entity/HTML kerak.
- Tugma uchun faqat `primary` (ko'k), `success` (yashil), `danger` (qizil) uslublari bor. `style` yuborilmasa tugma default ko'rinishda qoladi. HEX/RGB rang berib bo'lmaydi.
- Rang `KeyboardButton` va `InlineKeyboardButton` ikkalasida ham mavjud, lekin aiogram'da buning typed qo'llab-quvvatlashi **3.25.0** dan boshlangan.

## 1. Premium sticker'ni ushlash va qayta yuborish

Telegram `Message` obyektidagi `sticker` maydonini `Sticker` sifatida beradi. `Sticker.file_id` shu bot tomonidan qayta ishlatilishi mumkin bo'lgan identifikator. `sendSticker` esa mavjud Telegram faylini aynan `file_id` orqali yuborishni rasmiy ravishda qo'llaydi ([Message](https://core.telegram.org/bots/api#message), [Sticker](https://core.telegram.org/bots/api#sticker), [sendSticker](https://core.telegram.org/bots/api#sendsticker)).

Premium regular stickerda `Sticker.premium_animation` qo'shimcha effect animatsiyasini bildiradi. Asosiy sticker sifatida baribir `Sticker.file_id` ishlatiladi. `premium_animation` Bot API 6.1 da, 2022-06-20 kuni qo'shilgan ([Bot API 6.1 changelog](https://core.telegram.org/bots/api-changelog#june-20-2022)).

Aiogram oqimi:

```python
if message.sticker:
    sticker_file_id = message.sticker.file_id

await bot.send_sticker(chat_id=chat_id, sticker=sticker_file_id)
```

Sticker formati static `.WEBP`, animated `.TGS` yoki video `.WEBM` bo'lishi mumkin; `sendSticker` uchalasini qo'llaydi ([sendSticker](https://core.telegram.org/bots/api#sendsticker)). Premium akkaunt botga yuborgan sticker uchun alohida resend taqiqi rasmiy hujjatda ko'rsatilmagan.

`file_id` cheklovlari:

- faqat uni olgan ayni bot uchun ishlaydi, boshqa bot tokeniga ko'chirib bo'lmaydi;
- bitta fayl uchun bir nechta yaroqli `file_id` bo'lishi mumkin;
- `file_id` bilan qayta yuborishda kontent turini o'zgartirib bo'lmaydi;
- `file_unique_id` yuborish yoki yuklab olish uchun ishlamaydi.

Manba: [Telegram — Sending Files](https://core.telegram.org/bots/api#sending-files).

### Hozirgi repo holati

`utils/content.py` allaqachon `message.sticker.file_id` ni `type="sticker"` sifatida saqlaydi va `bot.send_sticker(...)` bilan yuboradi. Shuning uchun Telegram premium stickerni `Message.sticker` sifatida botga yetkazsa, mavjud oqimning o'zi ishlashi kerak. Muhim test — real Premium sticker yuborib, aynan o'sha ko'rinish/effect bilan qayta chiqishini tekshirish.

## 2. Custom emoji premium sticker bilan bir xil emas

Foydalanuvchi custom emoji'ni **matn ichida** yuborsa, u `Message.sticker` bo'lmaydi. `MessageEntity.type` qiymati `custom_emoji`, identifikatori esa `custom_emoji_id` bo'ladi. `getCustomEmojiStickers` bir so'rovda 200 tagacha shunday ID bo'yicha `Sticker` ma'lumotlarini qaytaradi ([MessageEntity](https://core.telegram.org/bots/api#messageentity), [getCustomEmojiStickers](https://core.telegram.org/bots/api#getcustomemojistickers)).

Ikki xil natija bor:

1. Custom emoji'ni katta standalone sticker sifatida yuborish kerak bo'lsa, `getCustomEmojiStickers([custom_emoji_id])` natijasidagi `Sticker.file_id` ni `sendSticker` ga berish API tiplaridan kelib chiqadigan yo'l. Lekin rasmiy hujjat bu konvertatsiyani alohida kafolatlamaydi; production'da real custom emoji bilan integration test qilish kerak. Standalone premium sticker uchun ishonchli yo'l — bevosita kelgan `Message.sticker.file_id`.
2. Uni matn orasida custom emoji ko'rinishida saqlash kerak bo'lsa, `custom_emoji_id` saqlanadi va outgoing matnda `custom_emoji` entity yoki HTML `<tg-emoji emoji-id="...">fallback</tg-emoji>` ishlatiladi ([Formatting options](https://core.telegram.org/bots/api#formatting-options)).

Matn ichida custom emoji yuborish huquqi cheklangan: bot Fragment'da qo'shimcha username sotib olgan bo'lishi yoki bot egasi Telegram Premium'ga ega bo'lishi va bot xabarni bevosita private/group/supergroup chatga yuborishi kerak. Bot egasi Premium bo'lgan holat Bot API 9.4 da, 2026-02-09 kuni qo'shilgan ([Bot API 9.4 changelog](https://core.telegram.org/bots/api-changelog#february-9-2026), [Formatting options](https://core.telegram.org/bots/api#formatting-options)).

## 3. Telegram tugma ranglari

Bot API 9.4, 2026-02-09 kuni `KeyboardButton.style` va `InlineKeyboardButton.style` maydonlarini qo'shgan ([changelog](https://core.telegram.org/bots/api-changelog#february-9-2026)). Har ikki maydon `String`, optional:

| Saqlanadigan qiymat | Telegram ko'rinishi | Tavsiya etilgan ma'no |
| --- | --- | --- |
| `NULL` / maydon yuborilmaydi | app-specific default | oddiy/neutral action |
| `primary` | ko'k | asosiy action |
| `success` | yashil | ijobiy action |
| `danger` | qizil | xavfli/destructive action |

Rasmiy maydon va qiymatlar: [KeyboardButton](https://core.telegram.org/bots/api#keyboardbutton), [InlineKeyboardButton](https://core.telegram.org/bots/api#inlinekeyboardbutton). Telegram faqat shu predefined qiymatlarni beradi; arbitrary HEX yoki RGB rang tanlash API'da yo'q. Client tema/dark mode sabab real rang soyasi biroz farq qilishi mumkin.

Default qiymat uchun `style="default"` yuborilmaydi — `style` umuman omit qilinadi (`None`).

## 4. Aiogram qo'llab-quvvatlashi

Aiogram **3.25.0**, 2026-02-10 kuni Bot API 9.4 supportini va har ikki button klassiga `style` maydonini qo'shgan ([aiogram 3.25.0 changelog](https://docs.aiogram.dev/en/v3.25.0/changelog.html#id1)). `ButtonStyle` enumida uch qiymat bor: `PRIMARY`, `SUCCESS`, `DANGER` ([ButtonStyle](https://docs.aiogram.dev/en/v3.25.0/api/enums/button_style.html)).

```python
from aiogram.enums import ButtonStyle
from aiogram.types import InlineKeyboardButton, KeyboardButton

default_button = KeyboardButton(text="Oddiy")
blue_button = KeyboardButton(text="Asosiy", style=ButtonStyle.PRIMARY)
green_button = KeyboardButton(text="Tasdiqlash", style=ButtonStyle.SUCCESS)
red_button = KeyboardButton(text="O'chirish", style=ButtonStyle.DANGER)

inline_green = InlineKeyboardButton(
    text="Tasdiqlash",
    callback_data="confirm",
    style=ButtonStyle.SUCCESS,
)
```

Aiogram API imzolari: [KeyboardButton](https://docs.aiogram.dev/en/v3.25.0/api/types/keyboard_button.html), [InlineKeyboardButton](https://docs.aiogram.dev/en/v3.25.0/api/types/inline_keyboard_button.html).

### Repo uchun talab

Tekshiruv boshida repo `requirements.txt` faylida `aiogram>=3.15,<4`, lokal muhitda esa `3.15.0` bor edi. Bu versiyada `ButtonStyle` va typed `style` maydoni yo'q. Rang funksiyasi uchun minimum versiya quyidagicha ko'tarildi:

```text
aiogram>=3.25,<4
```

## 5. Implementatsiya uchun tavsiya etilgan model

- `menu_items` jadvaliga nullable `button_style` ustuni: `NULL | primary | success | danger`.
- Default uchun `NULL`; schema migration eski qatorlarni `NULL` qoldiradi va ular default ko'rinishda qoladi.
- Admin UI'da: `⚪️ Oddiy`, `🔵 Asosiy`, `🟢 Yashil`, `🔴 Qizil` variantlari.
- DB ga yozishda faqat whitelist qiymat qabul qilinsin.
- Reply keyboard yasalganda `KeyboardButton(text=item.title, style=item.button_style)`; `None` bo'lsa aiogram maydonni yubormaydi.
- O'zgarish DB ustuni sabab migration, module/process dependency update va bot restart talab qiladi.

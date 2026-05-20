"""
Telegram Test Bot — bot-10.py
SQLite, 3 til, kanal integratsiyasi, testlar arxivi,
manbalar arxivi, o'quvchi statistikasi, ro'yxatdan o'tish.
"""

import logging
import os
import sqlite3
import statistics as stats_lib
from datetime import datetime, timezone, timedelta
from pathlib import Path

from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from ai_modul import (
    ai_jadvallar_yaratish,
    ai_javob_olish,
    admin_ai_javob,
    limit_tekshir,
    limit_oshir,
    profil_olish,
    profil_saqlash,
    profil_yangilash_ai,
    KUNLIK_LIMIT,
)

# ─────────────────────────────────────────────────────────────────────────────
# ⚙️  SOZLAMALAR
# ─────────────────────────────────────────────────────────────────────────────

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "8287874316:AAGfEAUwvGagajEYl1rhXZNfLdeOWNgDTmk")
ADMIN_ID   = int(os.environ.get("ADMIN_ID", "7710339509"))
KANAL_ID   = os.environ.get("KANAL_ID", "@AzizbekMaripov_Kimyo")
OTISH_BALI = 60
SAHIFA_HAJMI = 10

def kanal_link() -> str:
    """@username → https://t.me/username formatiga o'tkazadi."""
    if KANAL_ID.startswith("@"):
        return f"https://t.me/{KANAL_ID[1:]}"
    return KANAL_ID

DB_FAYL = Path("data/bot.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

UZ_TZ = timezone(timedelta(hours=5))

def hozirgi_vaqt() -> str:
    return datetime.now(UZ_TZ).strftime("%d.%m.%Y %H:%M")

# ─────────────────────────────────────────────────────────────────────────────
# 🌐 TIL TIZIMI
# ─────────────────────────────────────────────────────────────────────────────

MATNLAR = {
    "uz": {
        # Umumiy
        "til_tanlash"        : "🌐 Tilni tanlang:",
        "xush_kelibsiz"      : "👋 Xush kelibsiz!",
        "kanal_obuna"        : "⚠️ Botdan foydalanish uchun kanalga obuna bo'ling!\n\n📢 Kanal: [{kanal}]({kanal})\n\nObuna bo'lgach, /start bosing.",
        "obuna_tekshir"      : "✅ Tekshirish",

        # Ro'yxatdan o'tish
        "royxat_boshlash"    : "📋 Ro'yxatdan o'tish boshlandi!\n\nIltimos, quyidagi ma'lumotlarni kiriting.",
        "ism_familiya"       : "👤 To'liq ism-familiyangizni kiriting:\n\n_(Masalan: Karimov Alibek)_",
        "tuman"              : "🏘 Tumaningizni kiriting:\n\n_(Masalan: Yunusobod)_",
        "maktab"             : "🏫 Maktabingizni kiriting:\n\n_(Masalan: 45-maktab)_",
        "sinf"               : "📚 Sinfingizni kiriting:\n\n_(Masalan: 10-A)_",
        "yosh"               : "🎂 Yoshingizni kiriting:\n\n_(Masalan: 16)_",
        "kontakt"            : "📱 Telefon raqamingizni ulashing:",
        "kontakt_tugma"      : "📱 Kontaktni ulashish",
        "tasdiq"             : (
            "✅ *Ma'lumotlaringiz:*\n\n"
            "👤 {ism}\n"
            "🏘 {tuman}\n"
            "🏫 {maktab}\n"
            "📚 {sinf}\n"
            "🎂 {yosh} yosh\n"
            "📱 {telefon}\n\n"
            "Ma'lumotlar to'g'rimi?"
        ),
        "tasdiq_ha"          : "✅ Ha, to'g'ri",
        "tasdiq_yoq"         : "❌ Yo'q, qaytadan",
        "royxat_tugadi"      : "🎉 Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\nBotdan foydalanishingiz mumkin.",
        "yosh_xato"          : "❌ Yoshni to'g'ri kiriting (masalan: 16)",

        # Asosiy menyu
        "test_boshlash"      : "📄 Testni boshlash",
        "javob_yuborish"     : "📝 Javob yuborish",
        "natijam"            : "📊 Natijam",
        "mening_tarixim"     : "📈 Mening tarixim",
        "manbalar"           : "📖 Manbalar",
        "murojaat"           : "📨 Adminga murojaat",
        "sozlamalar"         : "⚙️ Sozlamalar",

        # Test jarayoni
        "test_ochiq_emas"    : "⏳ Test hali boshlanmagan yoki yakunlangan.",
        "pdf_yoq"            : "⚠️ Test fayli hali yuklanmagan. Admin bilan bog'laning.",
        "allaqachon_topshirdi": (
            "⚠️ Siz allaqachon test topshirdingiz!\n\n"
            "📊 Natijangiz: *{foiz}%* ({togri}/{jami})\n"
            "🕐 Vaqt: {vaqt}"
        ),
        "allaqachon_boshlagan": (
            "⚠️ Siz testni allaqachon boshlagansiz!\n\n"
            "{qolgan}\n\nJavob yuborish uchun 📝 tugmasini bosing."
        ),
        "taymer_boshlandi"   : (
            "✅ *Taymeringiz boshlandi!*\n\n"
            "⏱ Sizda *{daqiqa}* daqiqa bor.\n"
            "⚠️ *{ogohlantirish}* daqiqadan so'ng ogohlantirish keladi."
        ),
        "ogohlantirish"      : (
            "⚠️ *Diqqat! 10 daqiqa qoldi!*\n\n"
            "Javoblaringizni tezroq yuboring."
        ),
        "vaqt_tugadi"        : "⏰ Vaqtingiz tugadi! Javob qabul qilinmadi.",
        "nol_ball"           : (
            "⏰ *Vaqtingiz tugadi!*\n\n"
            "📊 Natijangiz: *0%* (0/{jami})\n\n"
            "Reyting tez orada e'lon qilinadi."
        ),
        "avval_boshlash"     : "⚠️ Avval 📄 *Testni boshlash* tugmasini bosing!",
        "qolgan_vaqt"        : "⏱ Qolgan vaqt: *{daqiqa}:{soniya}*",

        # Savol-javob
        "savol_matni"        : "📝 *{joriy}/{jami} — savol*\n\n{joriy}-savolga javobingiz?",
        "savol_tanlandi"     : "📝 *{joriy}/{jami} — savol*\n\n{joriy}-savolga javobingiz: *{harf}* ✅",
        "tasdiq_javob"       : (
            "📋 *Sizning javoblaringiz:*\n\n`{preview}`\n\n"
            "{qolgan}\n\nJavoblaringizni tasdiqlaysizmi?"
        ),
        "qaytadan"           : "🔄 Qaytadan boshlanmoqda...",

        # Natija (funksiyada to'g'ridan-to'g'ri yoziladi)
        "otdi"               : "O'tdingiz",
        "otmadi"             : "O'tmadingiz",

        # Tarix
        "tarix_yoq"          : "📭 Siz hali hech qanday test topshirmagansiz.",
        "tarix_matni"        : "📈 *Sizning test tarixingiz:*\n\n",
        "taqqoslama"         : (
            "📊 *{test_nomi} bo'yicha tahlil:*\n\n"
            "📈 Bu test: *{foiz}%*\n"
            "📊 O'rtacha: *{ortacha}%*\n"
            "{dinamika}\n\n"
            "{xulosa}"
        ),
        "osish"              : "📈 O'tgan testga nisbatan +{fark}% o'sish!",
        "tushish"            : "📉 O'tgan testga nisbatan -{fark}% tushish.",
        "barqaror"           : "➡️ Natija barqaror.",
        "birinchi_test"      : "🎯 Bu sizning birinchi testingiz!",
        "davom_eting"        : "💪 Davom eting, yaxshi natijalarga erishishingiz mumkin!",
        "ajoyib"             : "🌟 Ajoyib natija! Shunday davom eting!",

        # Manbalar
        "manbalar_yoq"       : "📭 Hozircha hech qanday manba yuklanmagan.",
        "manbalar_sarlavha"  : "📚 *Kimyo bo'yicha manbalar ({joriy}-{oxiri} / {jami}):*\n\n",
        "manbalar_tanla"     : "\nKerakli raqamni yuboring:",
        "manba_yoq"          : "❌ Bunday raqam yo'q. Qaytadan kiriting.",
        "sahifa_oldingi"     : "⬅️ Oldingi",
        "sahifa_keyingi"     : "Keyingi ➡️",
        "sahifa_raqam"       : "{joriy}/{jami} sahifa",

        # Murojaat
        "murojaat_boshlash"  : "📨 *Adminga murojaat*\n\nXabaringizni yozing:\n\nBekor qilish: /bekor",
        "murojaat_yuborildi" : "✅ Xabaringiz adminga yuborildi!\n\nJavob kelgach sizga xabar beriladi.",

        # Sozlamalar
        "sozlamalar_matni"   : "⚙️ *Sozlamalar*\n\nHozirgi til: 🇺🇿 O'zbek\n\nNimani o'zgartirmoqchisiz?",
        "til_ozgartirish"    : "🌐 Tilni o'zgartirish",
        "til_ozgartirildi"   : "✅ Til o'zgartirildi: 🇺🇿 O'zbek",

        # Bekor
        "bekor"              : "🚫 Bekor qilindi.",

        # AI Ximik
        "ai_ximik"           : "🧪 AI Ximik",
        "ai_chiqish"         : "🚪 AI dan chiqish",
        "ai_xush_keldi"      : (
            "🧪 *AI Ximik* ga xush kelibsiz!\n\n"
            "Kimyo bo\'yicha savollaringizni yozing.\n"
            "Men tushunishingizga yordam beraman.\n\n"
            "_Chiqish uchun 🚪 tugmasini bosing._"
        ),
        "ai_limit"           : (
            "⚠️ Bugungi {limit} ta savolingiz tugadi.\n\n"
            "Ertaga qaytib keling! 🌙"
        ),

        # Intriga
        "birinchi_orn"       : "⚡ Siz hozircha 1-o\'rindasiz!",
        "top3"               : "🔥 Siz hozircha TOP-3 ichida turibsiz!",
        "oxirgi_orn"         : "💡 Hali o'qish vaqti bor, shoshilmang!",
        "orta_orn"           : "💪 Oldingizda kuchli raqiblar bor, harakat qiling!",
        "birinchi_ishtirokchi": "🌟 Siz birinchi ishtirokchisiz!",
    },

    "ru": {
        "til_tanlash"        : "🌐 Выберите язык:",
        "xush_kelibsiz"      : "👋 Добро пожаловать!",
        "kanal_obuna"        : "⚠️ Для использования бота подпишитесь на канал!\n\n📢 Канал: [{kanal}]({kanal})\n\nПосле подписки нажмите /start.",
        "obuna_tekshir"      : "✅ Проверить",

        "royxat_boshlash"    : "📋 Начало регистрации!\n\nПожалуйста, введите следующие данные.",
        "ism_familiya"       : "👤 Введите ваше полное ФИО:\n\n_(Например: Каримов Алибек)_",
        "tuman"              : "🏘 Введите ваш район:\n\n_(Например: Юнусабад)_",
        "maktab"             : "🏫 Введите вашу школу:\n\n_(Например: Школа №45)_",
        "sinf"               : "📚 Введите ваш класс:\n\n_(Например: 10-А)_",
        "yosh"               : "🎂 Введите ваш возраст:\n\n_(Например: 16)_",
        "kontakt"            : "📱 Поделитесь номером телефона:",
        "kontakt_tugma"      : "📱 Поделиться контактом",
        "tasdiq"             : (
            "✅ *Ваши данные:*\n\n"
            "👤 {ism}\n"
            "🏘 {tuman}\n"
            "🏫 {maktab}\n"
            "📚 {sinf}\n"
            "🎂 {yosh} лет\n"
            "📱 {telefon}\n\n"
            "Данные верны?"
        ),
        "tasdiq_ha"          : "✅ Да, верно",
        "tasdiq_yoq"         : "❌ Нет, заново",
        "royxat_tugadi"      : "🎉 Регистрация прошла успешно!\n\nМожете пользоваться ботом.",
        "yosh_xato"          : "❌ Введите возраст правильно (например: 16)",

        "test_boshlash"      : "📄 Начать тест",
        "javob_yuborish"     : "📝 Отправить ответы",
        "natijam"            : "📊 Мои результаты",
        "mening_tarixim"     : "📈 Моя история",
        "manbalar"           : "📖 Материалы",
        "murojaat"           : "📨 Написать админу",
        "sozlamalar"         : "⚙️ Настройки",

        "test_ochiq_emas"    : "⏳ Тест ещё не начался или завершён.",
        "pdf_yoq"            : "⚠️ Файл теста ещё не загружен. Обратитесь к администратору.",
        "allaqachon_topshirdi": (
            "⚠️ Вы уже прошли тест!\n\n"
            "📊 Результат: *{foiz}%* ({togri}/{jami})\n"
            "🕐 Время: {vaqt}"
        ),
        "allaqachon_boshlagan": (
            "⚠️ Вы уже начали тест!\n\n"
            "{qolgan}\n\nНажмите 📝 для отправки ответов."
        ),
        "taymer_boshlandi"   : (
            "✅ *Таймер запущен!*\n\n"
            "⏱ У вас *{daqiqa}* минут.\n"
            "⚠️ Через *{ogohlantirish}* минут придёт напоминание."
        ),
        "ogohlantirish"      : "⚠️ *Внимание! Осталось 10 минут!*\n\nОтправьте ответы быстрее.",
        "vaqt_tugadi"        : "⏰ Время вышло! Ответ не принят.",
        "nol_ball"           : (
            "⏰ *Время вышло!*\n\n"
            "📊 Результат: *0%* (0/{jami})\n\n"
            "Рейтинг будет объявлен скоро."
        ),
        "avval_boshlash"     : "⚠️ Сначала нажмите 📄 *Начать тест*!",
        "qolgan_vaqt"        : "⏱ Осталось: *{daqiqa}:{soniya}*",

        "savol_matni"        : "📝 *{joriy}/{jami} — вопрос*\n\nВаш ответ на {joriy}-й вопрос?",
        "savol_tanlandi"     : "📝 *{joriy}/{jami} — вопрос*\n\nВаш ответ на {joriy}-й вопрос: *{harf}* ✅",
        "tasdiq_javob"       : (
            "📋 *Ваши ответы:*\n\n`{preview}`\n\n"
            "{qolgan}\n\nПодтвердить ответы?"
        ),
        "qaytadan"           : "🔄 Начинаем заново...",

        # Natija
        "otdi"               : "Сдали",
        "otmadi"             : "Не сдали",

        "tarix_yoq"          : "📭 Вы ещё не прошли ни одного теста.",
        "tarix_matni"        : "📈 *История ваших тестов:*\n\n",
        "taqqoslama"         : (
            "📊 *Анализ по тесту {test_nomi}:*\n\n"
            "📈 Этот тест: *{foiz}%*\n"
            "📊 Среднее: *{ortacha}%*\n"
            "{dinamika}\n\n"
            "{xulosa}"
        ),
        "osish"              : "📈 По сравнению с прошлым тестом +{fark}%!",
        "tushish"            : "📉 По сравнению с прошлым тестом -{fark}%.",
        "barqaror"           : "➡️ Результат стабильный.",
        "birinchi_test"      : "🎯 Это ваш первый тест!",
        "davom_eting"        : "💪 Продолжайте, вы можете добиться хороших результатов!",
        "ajoyib"             : "🌟 Отличный результат! Продолжайте в том же духе!",

        "manbalar_yoq"       : "📭 Пока материалы не загружены.",
        "manbalar_sarlavha"  : "📚 *Материалы по химии ({joriy}-{oxiri} / {jami}):*\n\n",
        "manbalar_tanla"     : "\nВведите нужный номер:",
        "manba_yoq"          : "❌ Такого номера нет. Введите ещё раз.",
        "sahifa_oldingi"     : "⬅️ Назад",
        "sahifa_keyingi"     : "Вперёд ➡️",
        "sahifa_raqam"       : "{joriy}/{jami} стр.",

        "murojaat_boshlash"  : "📨 *Написать админу*\n\nНапишите ваше сообщение:\n\nОтмена: /bekor",
        "murojaat_yuborildi" : "✅ Ваше сообщение отправлено!\n\nКогда придёт ответ, мы уведомим вас.",

        "sozlamalar_matni"   : "⚙️ *Настройки*\n\nТекущий язык: 🇷🇺 Русский\n\nЧто хотите изменить?",
        "til_ozgartirish"    : "🌐 Изменить язык",
        "til_ozgartirildi"   : "✅ Язык изменён: 🇷🇺 Русский",

        "bekor"              : "🚫 Отменено.",

        # AI Ximik
        "ai_ximik"           : "🧪 AI Химик",
        "ai_chiqish"         : "🚪 Выйти из AI",
        "ai_xush_keldi"      : (
            "🧪 *AI Химик*!\n\n"
            "Задавайте вопросы по химии.\n"
            "Я помогу вам понять.\n\n"
            "_Для выхода нажмите 🚪._"
        ),
        "ai_limit"           : (
            "⚠️ Ваш дневной лимит ({limit} вопросов) исчерпан.\n\n"
            "Возвращайтесь завтра! 🌙"
        ),

        "birinchi_orn"       : "⚡ Вы сейчас на 1-м месте!",
        "top3"               : "🔥 Вы сейчас в TOP-3!",
        "oxirgi_orn"         : "💡 Ещё есть время учиться, не спешите!",
        "orta_orn"           : "💪 Впереди сильные соперники, старайтесь!",
        "birinchi_ishtirokchi": "🌟 Вы первый участник!",
    },

    "en": {
        "til_tanlash"        : "🌐 Choose language:",
        "xush_kelibsiz"      : "👋 Welcome!",
        "kanal_obuna"        : "⚠️ To use the bot, please subscribe to the channel!\n\n📢 Channel: [{kanal}]({kanal})\n\nAfter subscribing, press /start.",
        "obuna_tekshir"      : "✅ Check",

        "royxat_boshlash"    : "📋 Registration started!\n\nPlease enter the following information.",
        "ism_familiya"       : "👤 Enter your full name:\n\n_(Example: Karimov Alibek)_",
        "tuman"              : "🏘 Enter your district:\n\n_(Example: Yunusobod)_",
        "maktab"             : "🏫 Enter your school:\n\n_(Example: School №45)_",
        "sinf"               : "📚 Enter your class:\n\n_(Example: 10-A)_",
        "yosh"               : "🎂 Enter your age:\n\n_(Example: 16)_",
        "kontakt"            : "📱 Share your phone number:",
        "kontakt_tugma"      : "📱 Share contact",
        "tasdiq"             : (
            "✅ *Your information:*\n\n"
            "👤 {ism}\n"
            "🏘 {tuman}\n"
            "🏫 {maktab}\n"
            "📚 {sinf}\n"
            "🎂 {yosh} years old\n"
            "📱 {telefon}\n\n"
            "Is the information correct?"
        ),
        "tasdiq_ha"          : "✅ Yes, correct",
        "tasdiq_yoq"         : "❌ No, re-enter",
        "royxat_tugadi"      : "🎉 Registration successful!\n\nYou can now use the bot.",
        "yosh_xato"          : "❌ Enter age correctly (example: 16)",

        "test_boshlash"      : "📄 Start test",
        "javob_yuborish"     : "📝 Submit answers",
        "natijam"            : "📊 My results",
        "mening_tarixim"     : "📈 My history",
        "manbalar"           : "📖 Materials",
        "murojaat"           : "📨 Contact admin",
        "sozlamalar"         : "⚙️ Settings",

        "test_ochiq_emas"    : "⏳ Test has not started or has ended.",
        "pdf_yoq"            : "⚠️ Test file not uploaded yet. Contact admin.",
        "allaqachon_topshirdi": (
            "⚠️ You have already submitted the test!\n\n"
            "📊 Result: *{foiz}%* ({togri}/{jami})\n"
            "🕐 Time: {vaqt}"
        ),
        "allaqachon_boshlagan": (
            "⚠️ You have already started the test!\n\n"
            "{qolgan}\n\nPress 📝 to submit answers."
        ),
        "taymer_boshlandi"   : (
            "✅ *Timer started!*\n\n"
            "⏱ You have *{daqiqa}* minutes.\n"
            "⚠️ Warning will come in *{ogohlantirish}* minutes."
        ),
        "ogohlantirish"      : "⚠️ *Attention! 10 minutes left!*\n\nSubmit your answers faster.",
        "vaqt_tugadi"        : "⏰ Time is up! Answer not accepted.",
        "nol_ball"           : (
            "⏰ *Time is up!*\n\n"
            "📊 Result: *0%* (0/{jami})\n\n"
            "Ranking will be announced soon."
        ),
        "avval_boshlash"     : "⚠️ First press 📄 *Start test*!",
        "qolgan_vaqt"        : "⏱ Time left: *{daqiqa}:{soniya}*",

        "savol_matni"        : "📝 *{joriy}/{jami} — question*\n\nYour answer to question {joriy}?",
        "savol_tanlandi"     : "📝 *{joriy}/{jami} — question*\n\nYour answer to question {joriy}: *{harf}* ✅",
        "tasdiq_javob"       : (
            "📋 *Your answers:*\n\n`{preview}`\n\n"
            "{qolgan}\n\nConfirm your answers?"
        ),
        "qaytadan"           : "🔄 Restarting...",

        # Natija
        "otdi"               : "Passed",
        "otmadi"             : "Failed",

        "tarix_yoq"          : "📭 You haven't taken any tests yet.",
        "tarix_matni"        : "📈 *Your test history:*\n\n",
        "taqqoslama"         : (
            "📊 *Analysis for {test_nomi}:*\n\n"
            "📈 This test: *{foiz}%*\n"
            "📊 Average: *{ortacha}%*\n"
            "{dinamika}\n\n"
            "{xulosa}"
        ),
        "osish"              : "📈 +{fark}% improvement from last test!",
        "tushish"            : "📉 -{fark}% drop from last test.",
        "barqaror"           : "➡️ Result is stable.",
        "birinchi_test"      : "🎯 This is your first test!",
        "davom_eting"        : "💪 Keep going, you can achieve great results!",
        "ajoyib"             : "🌟 Excellent result! Keep it up!",

        "manbalar_yoq"       : "📭 No materials uploaded yet.",
        "manbalar_sarlavha"  : "📚 *Chemistry materials ({joriy}-{oxiri} / {jami}):*\n\n",
        "manbalar_tanla"     : "\nEnter the number you need:",
        "manba_yoq"          : "❌ No such number. Try again.",
        "sahifa_oldingi"     : "⬅️ Previous",
        "sahifa_keyingi"     : "Next ➡️",
        "sahifa_raqam"       : "{joriy}/{jami} page",

        "murojaat_boshlash"  : "📨 *Contact admin*\n\nWrite your message:\n\nCancel: /bekor",
        "murojaat_yuborildi" : "✅ Your message has been sent!\n\nYou'll be notified when admin replies.",

        "sozlamalar_matni"   : "⚙️ *Settings*\n\nCurrent language: 🇬🇧 English\n\nWhat would you like to change?",
        "til_ozgartirish"    : "🌐 Change language",
        "til_ozgartirildi"   : "✅ Language changed: 🇬🇧 English",

        "bekor"              : "🚫 Cancelled.",

        # AI Ximik
        "ai_ximik"           : "🧪 AI Chemist",
        "ai_chiqish"         : "🚪 Exit AI",
        "ai_xush_keldi"      : (
            "🧪 *AI Chemist*!\n\n"
            "Ask your chemistry questions.\n"
            "I'll help you understand.\n\n"
            "_Press 🚪 to exit._"
        ),
        "ai_limit"           : (
            "⚠️ Your daily limit ({limit} questions) is used up.\n\n"
            "Come back tomorrow! 🌙"
        ),

        "birinchi_orn"       : "⚡ You are currently in 1st place!",
        "top3"               : "🔥 You are currently in TOP-3!",
        "oxirgi_orn"         : "💡 There's still time to study, don't rush!",
        "orta_orn"           : "💪 Strong competitors ahead, keep trying!",
        "birinchi_ishtirokchi": "🌟 You are the first participant!",
    }
}


def m(user_id: int, kalit: str, **kwargs) -> str:
    """Foydalanuvchi tiliga mos matnni qaytaradi."""
    til = foydalanuvchi_tili(user_id)
    matn = MATNLAR.get(til, MATNLAR["uz"]).get(kalit, f"[{kalit}]")
    if kwargs:
        try:
            matn = matn.format(**kwargs)
        except Exception:
            pass
    return matn


# ─────────────────────────────────────────────────────────────────────────────
# 🗃 SQLite MA'LUMOTLAR BAZASI
# ─────────────────────────────────────────────────────────────────────────────

def db_ulanish():
    DB_FAYL.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_FAYL)
    conn.row_factory = sqlite3.Row
    return conn


def db_yaratish():
    """Barcha jadvallarni yaratadi."""
    ai_jadvallar_yaratish()
    with db_ulanish() as conn:
        conn.executescript("""
        -- Foydalanuvchilar
        CREATE TABLE IF NOT EXISTS foydalanuvchilar (
            user_id     TEXT PRIMARY KEY,
            ism         TEXT,
            tuman       TEXT,
            maktab      TEXT,
            sinf        TEXT,
            yosh        INTEGER,
            telefon     TEXT,
            til         TEXT DEFAULT 'uz',
            royxatdan   INTEGER DEFAULT 0,
            qoshilgan   TEXT
        );

        -- Testlar arxivi
        CREATE TABLE IF NOT EXISTS testlar (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nomi            TEXT NOT NULL,
            pdf_file_id     TEXT,
            togri_javoblar  TEXT,
            vaqt_daqiqa     INTEGER DEFAULT 60,
            yaratilgan      TEXT,
            yakunlangan     TEXT,
            holat           TEXT DEFAULT 'ochiq'
        );

        -- Natijalar
        CREATE TABLE IF NOT EXISTS natijalar (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT,
            test_id         INTEGER,
            ism             TEXT,
            username        TEXT,
            togri           INTEGER DEFAULT 0,
            xato            INTEGER DEFAULT 0,
            topilmagan      INTEGER DEFAULT 0,
            jami            INTEGER DEFAULT 0,
            foiz            REAL DEFAULT 0.0,
            savol_natijalari TEXT,
            vaqt            TEXT,
            vaqt_tugadi     INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES foydalanuvchilar(user_id),
            FOREIGN KEY (test_id) REFERENCES testlar(id)
        );

        -- Manbalar arxivi
        CREATE TABLE IF NOT EXISTS manbalar (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nomi        TEXT NOT NULL,
            file_id     TEXT NOT NULL,
            fayl_turi   TEXT DEFAULT 'pdf',
            qoshilgan   TEXT
        );

        -- Murojaatlar
        CREATE TABLE IF NOT EXISTS murojaatlar (
            xabar_id    TEXT PRIMARY KEY,
            user_id     TEXT
        );

        -- Bot sozlamalari
        CREATE TABLE IF NOT EXISTS sozlamalar (
            kalit   TEXT PRIMARY KEY,
            qiymat  TEXT
        );

        -- Joriy test (faol test ID si)
        INSERT OR IGNORE INTO sozlamalar (kalit, qiymat)
        VALUES ('joriy_test_id', NULL);
        """)


# ─────────────────────────────────────────────────────────────────────────────
# 🔧 YORDAMCHI FUNKSIYALAR
# ─────────────────────────────────────────────────────────────────────────────

def foydalanuvchi_tili(user_id: int) -> str:
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT til FROM foydalanuvchilar WHERE user_id=?", (str(user_id),)
        ).fetchone()
    return row["til"] if row else "uz"


def foydalanuvchi_royxatdanmi(user_id: int) -> bool:
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT royxatdan FROM foydalanuvchilar WHERE user_id=?", (str(user_id),)
        ).fetchone()
    return bool(row and row["royxatdan"])


def joriy_test_olish():
    """Faol testni qaytaradi."""
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT qiymat FROM sozlamalar WHERE kalit='joriy_test_id'"
        ).fetchone()
        if not row or not row["qiymat"]:
            return None
        test = conn.execute(
            "SELECT * FROM testlar WHERE id=?", (row["qiymat"],)
        ).fetchone()
    return dict(test) if test else None


def togri_javoblar_parse(test: dict) -> dict:
    import json
    try:
        return {int(k): v for k, v in json.loads(test["togri_javoblar"]).items()}
    except Exception:
        return {}


def natija_bormi(user_id: int, test_id: int) -> dict | None:
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT * FROM natijalar WHERE user_id=? AND test_id=?",
            (str(user_id), test_id)
        ).fetchone()
    return dict(row) if row else None


def joriy_orn(user_id: int, test_id: int) -> tuple:
    with db_ulanish() as conn:
        rows = conn.execute(
            "SELECT user_id, foiz FROM natijalar WHERE test_id=? ORDER BY foiz DESC",
            (test_id,)
        ).fetchall()
    if not rows:
        return 1, 1
    jami = len(rows)
    for i, r in enumerate(rows, 1):
        if r["user_id"] == str(user_id):
            return i, jami
    return jami + 1, jami


def intriga_xabar(user_id: int, orn: int, jami: int) -> str:
    if jami <= 1:
        return m(user_id, "birinchi_ishtirokchi")
    if orn == 1:
        return m(user_id, "birinchi_orn")
    elif orn <= 3:
        return m(user_id, "top3")
    elif orn == jami:
        return m(user_id, "oxirgi_orn")
    return m(user_id, "orta_orn")


def qolgan_vaqt_matni(user_id: int, boshlangan: datetime, vaqt_daqiqa: int) -> str:
    utgan = (datetime.now(timezone.utc) - boshlangan).total_seconds() / 60
    qolgan = vaqt_daqiqa - utgan
    if qolgan <= 0:
        return "⏰ Vaqt tugagan"
    d = int(qolgan)
    s = int((qolgan - d) * 60)
    return m(user_id, "qolgan_vaqt", daqiqa=d, soniya=f"{s:02d}")


def javoblarni_tekshir(foydalanuvchi_javoblari: dict, togri_j: dict):
    togri = xato = topilmagan = 0
    savol_natijalari = {}
    for raqam in sorted(togri_j.keys()):
        togri_javob = togri_j[raqam].upper()
        if raqam in foydalanuvchi_javoblari:
            if str(foydalanuvchi_javoblari[raqam]).upper() == togri_javob:
                togri += 1
                savol_natijalari[raqam] = "togri"
            else:
                xato += 1
                savol_natijalari[raqam] = "xato"
        else:
            topilmagan += 1
            savol_natijalari[raqam] = "topilmagan"
    jami = len(togri_j)
    foiz = round((togri / jami) * 100, 1) if jami > 0 else 0.0
    return togri, xato, topilmagan, foiz, savol_natijalari


def matnni_parse_qil(matn: str):
    import re
    javoblar = {}
    xatolar = []
    for qism in matn.strip().upper().split():
        m_re = re.fullmatch(r"(\d+)([A-D])", qism)
        if m_re:
            javoblar[int(m_re.group(1))] = m_re.group(2)
        elif qism:
            xatolar.append(qism)
    return javoblar, xatolar


# RAM taymerlar
_faol_taymerlar: dict = {}


def taymer_boshlash(user_id: int, context, ism="—", username="—", vaqt_daqiqa=60):
    uid_str = str(user_id)
    _faol_taymerlar[uid_str] = datetime.now(timezone.utc)
    ogohlantirish_d = vaqt_daqiqa - 10
    if ogohlantirish_d > 0:
        context.job_queue.run_once(
            ogohlantirish_job,
            when=ogohlantirish_d * 60,
            data={"user_id": user_id},
            name=f"ogohlantirish_{user_id}"
        )
    context.job_queue.run_once(
        vaqt_tugadi_job,
        when=vaqt_daqiqa * 60,
        data={"user_id": user_id, "ism": ism, "username": username},
        name=f"vaqt_tugadi_{user_id}"
    )


def taymer_bekor_qilish(user_id: int, context):
    _faol_taymerlar.pop(str(user_id), None)
    for nom in [f"ogohlantirish_{user_id}", f"vaqt_tugadi_{user_id}"]:
        for job in context.job_queue.get_jobs_by_name(nom):
            job.schedule_removal()


async def nol_ball_saqlash(user_id: int, bot, ism="—", username="—"):
    import json as _json
    uid_str = str(user_id)
    test = joriy_test_olish()
    if not test:
        return
    test_id = test["id"]

    if natija_bormi(user_id, test_id):
        return

    togri_j = togri_javoblar_parse(test)
    jami = len(togri_j)
    savol_natijalari = {str(r): "topilmagan" for r in togri_j}

    with db_ulanish() as conn:
        conn.execute("""
            INSERT INTO natijalar
            (user_id, test_id, ism, username, togri, xato, topilmagan,
             jami, foiz, savol_natijalari, vaqt, vaqt_tugadi)
            VALUES (?,?,?,?,0,0,?,?,0.0,?,?,1)
        """, (uid_str, test_id, ism, username, jami, jami,
              _json.dumps(savol_natijalari), hozirgi_vaqt()))

    _faol_taymerlar.pop(uid_str, None)

    try:
        await bot.send_message(
            chat_id=user_id,
            text=m(user_id, "nol_ball", jami=jami),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Nol ball xabarida xatolik (user {user_id}): {e}")


async def ogohlantirish_job(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data["user_id"]
    uid_str = str(user_id)
    test = joriy_test_olish()
    if not test or natija_bormi(user_id, test["id"]):
        return
    if uid_str not in _faol_taymerlar:
        return
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=m(user_id, "ogohlantirish"),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ogohlantirish xabarida xatolik: {e}")


async def vaqt_tugadi_job(context: ContextTypes.DEFAULT_TYPE):
    user_id  = context.job.data["user_id"]
    ism      = context.job.data.get("ism", "—")
    username = context.job.data.get("username", "—")
    await nol_ball_saqlash(user_id, context.bot, ism=ism, username=username)


async def xabar_yuborish_chunks(update: Update, matn: str, limit: int = 4000):
    qatorlar = matn.split("\n")
    chunk = ""
    for qator in qatorlar:
        if len(chunk) + len(qator) + 1 > limit:
            if chunk:
                await update.message.reply_text(chunk, parse_mode="Markdown")
            chunk = qator + "\n"
        else:
            chunk += qator + "\n"
    if chunk.strip():
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def obuna_tekshir(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=KANAL_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 🔘 TUGMACHALAR
# ─────────────────────────────────────────────────────────────────────────────

def til_tugmalari(sozlama: bool = False):
    prefix = "sozlama_til_" if sozlama else "til_"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data=f"{prefix}uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data=f"{prefix}ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data=f"{prefix}en"),
    ]])


def obuna_tugmasi(user_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            m(user_id, "obuna_tekshir"),
            callback_data="obuna_tekshir"
        )
    ]])


def foydalanuvchi_tugmalari(user_id: int):
    return ReplyKeyboardMarkup([
        [KeyboardButton(m(user_id, "test_boshlash"))],
        [KeyboardButton(m(user_id, "javob_yuborish")),
         KeyboardButton(m(user_id, "natijam"))],
        [KeyboardButton(m(user_id, "mening_tarixim")),
         KeyboardButton(m(user_id, "manbalar"))],
        [KeyboardButton(m(user_id, "murojaat")),
         KeyboardButton(m(user_id, "sozlamalar"))],
        [KeyboardButton(m(user_id, "ai_ximik"))],
    ], resize_keyboard=True)


def admin_tugmalari():
    test = joriy_test_olish()
    test_tugma = "⏹ Testni yakunlash" if (test and test["holat"] == "ochiq") else "▶️ Testni boshlash"
    return ReplyKeyboardMarkup([
        [KeyboardButton(test_tugma)],
        [KeyboardButton("🔑 Kalit o'zgartirish"), KeyboardButton("✏️ Test nomi")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("📢 E'lon qilish")],
        [KeyboardButton("📖 Manba qo'shish"), KeyboardButton("🗑 Manba o'chirish")],
        [KeyboardButton("🔄 Natijalarni tozalash"), KeyboardButton("👁 Joriy kalit")],
        [KeyboardButton("👥 Foydalanuvchilar statistikasi")],
        [KeyboardButton("🧪 AI Maslahat")],
    ], resize_keyboard=True)


def ai_tugmasi(user_id: int):
    return ReplyKeyboardMarkup([
        [KeyboardButton(m(user_id, "ai_chiqish"))],
    ], resize_keyboard=True)


def javob_tugmalari():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("A", callback_data="javob_A"),
        InlineKeyboardButton("B", callback_data="javob_B"),
        InlineKeyboardButton("C", callback_data="javob_C"),
        InlineKeyboardButton("D", callback_data="javob_D"),
    ]])


def tasdiq_tugmalari(user_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(m(user_id, "tasdiq_ha"), callback_data="tasdiq_ha"),
        InlineKeyboardButton(m(user_id, "tasdiq_yoq"), callback_data="tasdiq_yoq"),
    ]])


def royxat_tasdiq_tugmalari(user_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(m(user_id, "tasdiq_ha"), callback_data="royxat_tasdiq_ha"),
        InlineKeyboardButton(m(user_id, "tasdiq_yoq"), callback_data="royxat_tasdiq_yoq"),
    ]])


def sozlamalar_tugmalari(user_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(m(user_id, "til_ozgartirish"), callback_data="sozlama_til"),
    ]])


def manbalar_sahifa_tugmalari(user_id: int, joriy_sahifa: int, jami_sahifa: int):
    qator = []
    if joriy_sahifa > 1:
        qator.append(InlineKeyboardButton(
            m(user_id, "sahifa_oldingi"),
            callback_data=f"manba_sahifa_{joriy_sahifa - 1}"
        ))
    qator.append(InlineKeyboardButton(
        m(user_id, "sahifa_raqam", joriy=joriy_sahifa, jami=jami_sahifa),
        callback_data="manba_sahifa_info"
    ))
    if joriy_sahifa < jami_sahifa:
        qator.append(InlineKeyboardButton(
            m(user_id, "sahifa_keyingi"),
            callback_data=f"manba_sahifa_{joriy_sahifa + 1}"
        ))
    return InlineKeyboardMarkup([qator])


# ─────────────────────────────────────────────────────────────────────────────
# 📌 ConversationHandler holatlari
# ─────────────────────────────────────────────────────────────────────────────

(
    TIL_TANLASH,
    ROYXAT_ISM, ROYXAT_TUMAN, ROYXAT_MAKTAB,
    ROYXAT_SINF, ROYXAT_YOSH, ROYXAT_KONTAKT,
    ROYXAT_TASDIQ,
    JAVOB_KUTILMOQDA,
    KALIT_KUTILMOQDA,
    TESTNOM_KUTILMOQDA,
    MUROJAAT_KUTILMOQDA,
    VAQT_KUTILMOQDA,
    SAVOL_KUTILMOQDA,
    TASDIQ_KUTILMOQDA,
    MANBA_NOM_KUTILMOQDA,
    MANBA_OCHIR_KUTILMOQDA,
    KANAL_ELON_TASDIQ,
    AI_SUHBAT,
) = range(19)


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 /start
# ─────────────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == ADMIN_ID:
        await update.message.reply_text(
            f"👋 Salom, Admin!\n\n🤖 Bot boshqaruv paneli",
            reply_markup=admin_tugmalari()
        )
        return JAVOB_KUTILMOQDA

    # Til tanlash
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT til FROM foydalanuvchilar WHERE user_id=?", (str(user.id),)
        ).fetchone()

    if not row:
        await update.message.reply_text(
            "🌐 Tilni tanlang / Выберите язык / Choose language:",
            reply_markup=til_tugmalari(sozlama=False)
        )
        return TIL_TANLASH

    # Kanalga obuna tekshiruvi
    if not await obuna_tekshir(context.bot, user.id):
        await update.message.reply_text(
            m(user.id, "kanal_obuna", kanal=kanal_link()),
            parse_mode="Markdown",
            reply_markup=obuna_tugmasi(user.id)
        )
        return JAVOB_KUTILMOQDA

    # Ro'yxatdan o'tganmi?
    if not foydalanuvchi_royxatdanmi(user.id):
        await update.message.reply_text(
            m(user.id, "royxat_boshlash"),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            m(user.id, "ism_familiya"),
            parse_mode="Markdown"
        )
        return ROYXAT_ISM

    # Hamma tekshiruvlar o'tdi
    test = joriy_test_olish()
    test_holat = "✅ Test ochiq" if (test and test["holat"] == "ochiq") else "⏳ Test hali boshlanmagan"
    await update.message.reply_text(
        f"{m(user.id, 'xush_kelibsiz')}\n\n{test_holat}",
        parse_mode="Markdown",
        reply_markup=foydalanuvchi_tugmalari(user.id)
    )
    return JAVOB_KUTILMOQDA


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 TIL TANLASH
# ─────────────────────────────────────────────────────────────────────────────

async def til_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    til  = query.data[4:]  # til_uz → uz

    with db_ulanish() as conn:
        conn.execute("""
            INSERT INTO foydalanuvchilar (user_id, til, qoshilgan)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET til=excluded.til
        """, (str(user.id), til, hozirgi_vaqt()))

    await query.edit_message_text(
        f"✅ {['🇺🇿 O\'zbek', '🇷🇺 Русский', '🇬🇧 English'][['uz','ru','en'].index(til)]}"
    )

    # Kanalga obuna tekshiruvi
    if not await obuna_tekshir(context.bot, user.id):
        await query.message.reply_text(
            m(user.id, "kanal_obuna", kanal=kanal_link()),
            parse_mode="Markdown",
            reply_markup=obuna_tugmasi(user.id)
        )
        return JAVOB_KUTILMOQDA

    await query.message.reply_text(
        m(user.id, "royxat_boshlash"),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await query.message.reply_text(
        m(user.id, "ism_familiya"),
        parse_mode="Markdown"
    )
    return ROYXAT_ISM


async def obuna_tekshir_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if not await obuna_tekshir(context.bot, user.id):
        await query.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        return JAVOB_KUTILMOQDA

    await query.answer()
    await query.edit_message_text("✅ Obuna tasdiqlandi!")

    if not foydalanuvchi_royxatdanmi(user.id):
        await query.message.reply_text(
            m(user.id, "royxat_boshlash"),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        await query.message.reply_text(
            m(user.id, "ism_familiya"),
            parse_mode="Markdown"
        )
        return ROYXAT_ISM

    await query.message.reply_text(
        m(user.id, "xush_kelibsiz"),
        reply_markup=foydalanuvchi_tugmalari(user.id)
    )
    return JAVOB_KUTILMOQDA


# ─────────────────────────────────────────────────────────────────────────────
# 📋 RO'YXATDAN O'TISH
# ─────────────────────────────────────────────────────────────────────────────

async def royxat_ism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ism  = update.message.text.strip()
    if len(ism) < 3:
        await update.message.reply_text("❌ Ism-familiya to'liq kiriting.")
        return ROYXAT_ISM
    context.user_data["royxat"] = {"ism": ism}
    await update.message.reply_text(m(user.id, "tuman"), parse_mode="Markdown")
    return ROYXAT_TUMAN


async def royxat_tuman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data["royxat"]["tuman"] = update.message.text.strip()
    await update.message.reply_text(m(user.id, "maktab"), parse_mode="Markdown")
    return ROYXAT_MAKTAB


async def royxat_maktab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data["royxat"]["maktab"] = update.message.text.strip()
    await update.message.reply_text(m(user.id, "sinf"), parse_mode="Markdown")
    return ROYXAT_SINF


async def royxat_sinf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    context.user_data["royxat"]["sinf"] = update.message.text.strip()
    await update.message.reply_text(m(user.id, "yosh"), parse_mode="Markdown")
    return ROYXAT_YOSH


async def royxat_yosh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    matn = update.message.text.strip()
    if not matn.isdigit() or not (10 <= int(matn) <= 100):
        await update.message.reply_text(m(user.id, "yosh_xato"))
        return ROYXAT_YOSH
    context.user_data["royxat"]["yosh"] = int(matn)
    await update.message.reply_text(
        m(user.id, "kontakt"),
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(m(user.id, "kontakt_tugma"), request_contact=True)]],
            resize_keyboard=True, one_time_keyboard=True
        )
    )
    return ROYXAT_KONTAKT


async def royxat_kontakt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    kontakt = update.message.contact
    if not kontakt:
        await update.message.reply_text(m(user.id, "kontakt"))
        return ROYXAT_KONTAKT

    context.user_data["royxat"]["telefon"] = kontakt.phone_number
    r = context.user_data["royxat"]

    await update.message.reply_text(
        m(user.id, "tasdiq",
          ism=r["ism"], tuman=r["tuman"], maktab=r["maktab"],
          sinf=r["sinf"], yosh=r["yosh"], telefon=r["telefon"]),
        parse_mode="Markdown",
        reply_markup=royxat_tasdiq_tugmalari(user.id)
    )
    return ROYXAT_TASDIQ


async def royxat_tasdiq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user

    if query.data == "royxat_tasdiq_yoq":
        context.user_data.pop("royxat", None)
        await query.edit_message_text("🔄 Qaytadan boshlanmoqda...")
        await query.message.reply_text(
            m(user.id, "ism_familiya"), parse_mode="Markdown"
        )
        return ROYXAT_ISM

    r = context.user_data.get("royxat", {})
    with db_ulanish() as conn:
        conn.execute("""
            INSERT INTO foydalanuvchilar
            (user_id, ism, tuman, maktab, sinf, yosh, telefon, til, royxatdan, qoshilgan)
            VALUES (?,?,?,?,?,?,?,?,1,?)
            ON CONFLICT(user_id) DO UPDATE SET
            ism=excluded.ism, tuman=excluded.tuman, maktab=excluded.maktab,
            sinf=excluded.sinf, yosh=excluded.yosh, telefon=excluded.telefon,
            royxatdan=1
        """, (str(user.id), r.get("ism"), r.get("tuman"), r.get("maktab"),
              r.get("sinf"), r.get("yosh"), r.get("telefon"),
              foydalanuvchi_tili(user.id), hozirgi_vaqt()))

    context.user_data.pop("royxat", None)
    await query.edit_message_text(m(user.id, "royxat_tugadi"), parse_mode="Markdown")
    await query.message.reply_text(
        m(user.id, "xush_kelibsiz"),
        reply_markup=foydalanuvchi_tugmalari(user.id)
    )
    return JAVOB_KUTILMOQDA


# ─────────────────────────────────────────────────────────────────────────────
# 📨 ASOSIY XABAR QABUL QILISH
# ─────────────────────────────────────────────────────────────────────────────

async def javob_qabul_qil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user        = update.effective_user
    matn        = update.message.text.strip()
    uid_str     = str(user.id)

    # ── Manba raqami (faqat raqam kiritilsa va manbalar ko'rsatilgan bo'lsa) ─
    if matn.isdigit() and context.user_data.get("manbalar_sahifa"):
        return await manba_raqam_qabul(update, context)

    # ── 📄 Testni boshlash ──────────────────────────────────────────────────
    if matn == m(user.id, "test_boshlash"):
        test = joriy_test_olish()
        if not test or test["holat"] != "ochiq":
            await update.message.reply_text(m(user.id, "test_ochiq_emas"))
            return JAVOB_KUTILMOQDA

        if not test["pdf_file_id"]:
            await update.message.reply_text(m(user.id, "pdf_yoq"))
            return JAVOB_KUTILMOQDA

        test_id = test["id"]
        if natija_bormi(user.id, test_id):
            n = natija_bormi(user.id, test_id)
            await update.message.reply_text(
                m(user.id, "allaqachon_topshirdi",
                  foiz=n["foiz"], togri=n["togri"],
                  jami=n["jami"], vaqt=n["vaqt"]),
                parse_mode="Markdown"
            )
            return JAVOB_KUTILMOQDA

        if uid_str in _faol_taymerlar:
            boshlangan = _faol_taymerlar[uid_str]
            qolgan = qolgan_vaqt_matni(user.id, boshlangan, test["vaqt_daqiqa"])
            await update.message.reply_text(
                m(user.id, "allaqachon_boshlagan", qolgan=qolgan),
                parse_mode="Markdown"
            )
            return JAVOB_KUTILMOQDA

        await context.bot.send_document(
            chat_id=user.id,
            document=test["pdf_file_id"],
            caption=f"📝 *{test['nomi']}*\n⏱ {test['vaqt_daqiqa']} daqiqa",
            parse_mode="Markdown"
        )
        ism      = user.first_name or "—"
        username = f"@{user.username}" if user.username else "—"
        taymer_boshlash(user.id, context, ism=ism, username=username,
                        vaqt_daqiqa=test["vaqt_daqiqa"])
        ogohlantirish_d = test["vaqt_daqiqa"] - 10
        await update.message.reply_text(
            m(user.id, "taymer_boshlandi",
              daqiqa=test["vaqt_daqiqa"],
              ogohlantirish=ogohlantirish_d),
            parse_mode="Markdown",
            reply_markup=foydalanuvchi_tugmalari(user.id)
        )
        return JAVOB_KUTILMOQDA

    # ── 📊 Natijam ──────────────────────────────────────────────────────────
    if matn == m(user.id, "natijam"):
        await mening_natijam(update, context)
        return JAVOB_KUTILMOQDA

    # ── 📈 Mening tarixim ───────────────────────────────────────────────────
    if matn == m(user.id, "mening_tarixim"):
        await mening_tarixim(update, context)
        return JAVOB_KUTILMOQDA

    # ── 📖 Manbalar ─────────────────────────────────────────────────────────
    if matn == m(user.id, "manbalar"):
        await manbalar_korsatish(update, context, sahifa=1)
        return JAVOB_KUTILMOQDA

    # ── 📨 Murojaat ─────────────────────────────────────────────────────────
    if matn == m(user.id, "murojaat"):
        await update.message.reply_text(
            m(user.id, "murojaat_boshlash"),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )
        return MUROJAAT_KUTILMOQDA

    # ── ⚙️ Sozlamalar ───────────────────────────────────────────────────────
    if matn == m(user.id, "sozlamalar"):
        await update.message.reply_text(
            m(user.id, "sozlamalar_matni"),
            parse_mode="Markdown",
            reply_markup=sozlamalar_tugmalari(user.id)
        )
        return JAVOB_KUTILMOQDA

    # ── 🧪 AI Ximik ─────────────────────────────────────────────────────────
    if matn == m(user.id, "ai_ximik"):
        return await ai_ximik_boshlash(update, context)

    # ── 📝 Javob yuborish ───────────────────────────────────────────────────
    if matn == m(user.id, "javob_yuborish"):
        test = joriy_test_olish()
        if not test or test["holat"] != "ochiq":
            await update.message.reply_text(m(user.id, "test_ochiq_emas"))
            return JAVOB_KUTILMOQDA

        test_id = test["id"]
        if natija_bormi(user.id, test_id):
            n = natija_bormi(user.id, test_id)
            await update.message.reply_text(
                m(user.id, "allaqachon_topshirdi",
                  foiz=n["foiz"], togri=n["togri"],
                  jami=n["jami"], vaqt=n["vaqt"]),
                parse_mode="Markdown"
            )
            return JAVOB_KUTILMOQDA

        if uid_str not in _faol_taymerlar:
            await update.message.reply_text(
                m(user.id, "avval_boshlash"), parse_mode="Markdown"
            )
            return JAVOB_KUTILMOQDA

        boshlangan   = _faol_taymerlar[uid_str]
        utgan_daqiqa = (datetime.now(timezone.utc) - boshlangan).total_seconds() / 60
        if utgan_daqiqa >= test["vaqt_daqiqa"]:
            await nol_ball_saqlash(user.id, context.bot)
            await update.message.reply_text(m(user.id, "vaqt_tugadi"))
            return JAVOB_KUTILMOQDA

        qolgan = qolgan_vaqt_matni(user.id, boshlangan, test["vaqt_daqiqa"])
        context.user_data["joriy_savol"]         = 1
        context.user_data["kiritilgan_javoblar"] = {}
        await update.message.reply_text(qolgan, parse_mode="Markdown")
        await savol_yuborish(update, context, test)
        return SAVOL_KUTILMOQDA

    # ── Admin tugmalari ─────────────────────────────────────────────────────
    if user.id == ADMIN_ID:
        if matn == "▶️ Testni boshlash":
            return await vaqt_sorash(update, context)
        elif matn == "⏹ Testni yakunlash":
            await test_yakunlash(update, context)
            return JAVOB_KUTILMOQDA
        elif matn == "🔑 Kalit o'zgartirish":
            return await kalit_boshlash(update, context)
        elif matn == "✏️ Test nomi":
            return await testnom_boshlash(update, context)
        elif matn == "📊 Statistika":
            await statistika(update, context)
            return JAVOB_KUTILMOQDA
        elif matn == "📢 E'lon qilish":
            return await elon_boshlash(update, context)
        elif matn == "📖 Manba qo'shish":
            return await manba_qoshish_boshlash(update, context)
        elif matn == "🗑 Manba o'chirish":
            return await manba_ochirish_boshlash(update, context)
        elif matn == "🔄 Natijalarni tozalash":
            await reset(update, context)
            return JAVOB_KUTILMOQDA
        elif matn == "👁 Joriy kalit":
            await holat_korsatish(update, context)
            return JAVOB_KUTILMOQDA
        elif matn == "👥 Foydalanuvchilar statistikasi":
            await foydalanuvchilar_statistikasi(update, context)
            return JAVOB_KUTILMOQDA
        elif matn == "🧪 AI Maslahat":
            return await ai_ximik_boshlash(update, context)

    return JAVOB_KUTILMOQDA


# ─────────────────────────────────────────────────────────────────────────────
# 📊 NATIJAM
# ─────────────────────────────────────────────────────────────────────────────

async def mening_natijam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user    = update.effective_user
    uid_str = str(user.id)
    test    = joriy_test_olish()

    if not test:
        await update.message.reply_text(m(user.id, "test_ochiq_emas"))
        return

    if uid_str in _faol_taymerlar and not natija_bormi(user.id, test["id"]):
        boshlangan = _faol_taymerlar[uid_str]
        qolgan     = qolgan_vaqt_matni(user.id, boshlangan, test["vaqt_daqiqa"])
        await update.message.reply_text(f"📭 Hali javob yubormadingiz.\n\n{qolgan}",
                                        parse_mode="Markdown")
        return

    n = natija_bormi(user.id, test["id"])
    if not n:
        await update.message.reply_text(m(user.id, "test_ochiq_emas"))
        return

    orn, jami_ish = joriy_orn(user.id, test["id"])
    emoji         = "✅" if n["foiz"] >= OTISH_BALI else "❌"
    holat_soz     = m(user.id, "otdi") if n["foiz"] >= OTISH_BALI else m(user.id, "otmadi")
    intriga       = intriga_xabar(user.id, orn, jami_ish)
    vaqt_belgi    = "\n⏰ *Vaqt tugab topshirildi*" if n["vaqt_tugadi"] else ""

    await update.message.reply_text(
        f"📊 *{test['nomi']} — Natijangiz*\n"
        f"{'─'*28}\n"
        f"✅ To'g'ri: *{n['togri']}/{n['jami']}*\n"
        f"❌ Xato: *{n['xato']}*\n"
        f"⬜ Javob yo'q: *{n['topilmagan']}*\n"
        f"📈 Foiz: *{n['foiz']}%*\n"
        f"{emoji} *{holat_soz}!*\n"
        f"🏅 O'rningiz: *{orn}/{jami_ish}*\n"
        f"🕐 {n['vaqt']}"
        f"{vaqt_belgi}\n\n"
        f"{intriga}",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 📈 MENING TARIXIM
# ─────────────────────────────────────────────────────────────────────────────

async def mening_tarixim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with db_ulanish() as conn:
        rows = conn.execute("""
            SELECT n.*, t.nomi as test_nomi
            FROM natijalar n
            JOIN testlar t ON n.test_id = t.id
            WHERE n.user_id = ?
            ORDER BY n.id ASC
        """, (str(user.id),)).fetchall()

    if not rows:
        await update.message.reply_text(m(user.id, "tarix_yoq"))
        return

    matn = m(user.id, "tarix_matni")
    foizlar = []
    for i, r in enumerate(rows, 1):
        emoji = "✅" if r["foiz"] >= OTISH_BALI else "❌"
        vt    = " ⏰" if r["vaqt_tugadi"] else ""
        matn += (
            f"{i}. *{r['test_nomi']}*{vt}\n"
            f"   {emoji} {r['foiz']}% | ✅{r['togri']}/❌{r['xato']}/⬜{r['topilmagan']} | 🕐{r['vaqt']}\n\n"
        )
        foizlar.append(r["foiz"])

    if len(foizlar) >= 2:
        ortacha = round(sum(foizlar) / len(foizlar), 1)
        oxirgi  = foizlar[-1]
        oldingi = foizlar[-2]
        fark    = round(abs(oxirgi - oldingi), 1)

        if oxirgi > oldingi:
            dinamika = m(user.id, "osish", fark=fark)
        elif oxirgi < oldingi:
            dinamika = m(user.id, "tushish", fark=fark)
        else:
            dinamika = m(user.id, "barqaror")

        xulosa = m(user.id, "ajoyib") if ortacha >= OTISH_BALI else m(user.id, "davom_eting")
        matn += (
            f"{'─'*28}\n"
            f"📊 O'rtacha: *{ortacha}%*\n"
            f"{dinamika}\n{xulosa}"
        )

    await xabar_yuborish_chunks(update, matn)


# ─────────────────────────────────────────────────────────────────────────────
# 📝 SAVOL-JAVOB JARAYONI
# ─────────────────────────────────────────────────────────────────────────────

async def savol_yuborish(update: Update, context: ContextTypes.DEFAULT_TYPE, test: dict):
    joriy = context.user_data["joriy_savol"]
    jami  = len(togri_javoblar_parse(test))
    await update.message.reply_text(
        m(update.effective_user.id, "savol_matni", joriy=joriy, jami=jami),
        parse_mode="Markdown",
        reply_markup=javob_tugmalari()
    )


async def savol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    uid_str = str(user.id)
    test    = joriy_test_olish()

    if not test:
        await query.edit_message_text("❌ Test topilmadi.")
        return JAVOB_KUTILMOQDA

    # Vaqt tekshiruvi
    if uid_str in _faol_taymerlar:
        boshlangan   = _faol_taymerlar[uid_str]
        utgan_daqiqa = (datetime.now(timezone.utc) - boshlangan).total_seconds() / 60
        if utgan_daqiqa >= test["vaqt_daqiqa"]:
            await nol_ball_saqlash(user.id, context.bot)
            await query.edit_message_text(m(user.id, "vaqt_tugadi"))
            return JAVOB_KUTILMOQDA

    harf  = query.data.split("_")[1]
    joriy = context.user_data.get("joriy_savol")
    jami  = len(togri_javoblar_parse(test))

    if joriy is None:
        await query.message.reply_text("/start bosing.")
        return ConversationHandler.END

    context.user_data["kiritilgan_javoblar"][joriy] = harf
    await query.edit_message_text(
        m(user.id, "savol_tanlandi", joriy=joriy, jami=jami, harf=harf),
        parse_mode="Markdown"
    )

    if joriy >= jami:
        javoblar = context.user_data["kiritilgan_javoblar"]
        preview  = " ".join([f"{r}{j}" for r, j in sorted(javoblar.items())])
        boshlangan = _faol_taymerlar.get(uid_str, datetime.now(timezone.utc))
        qolgan   = qolgan_vaqt_matni(user.id, boshlangan, test["vaqt_daqiqa"])
        await query.message.reply_text(
            m(user.id, "tasdiq_javob", preview=preview, qolgan=qolgan),
            parse_mode="Markdown",
            reply_markup=tasdiq_tugmalari(user.id)
        )
        return TASDIQ_KUTILMOQDA
    else:
        context.user_data["joriy_savol"] += 1
        joriy_yangi = context.user_data["joriy_savol"]
        await query.message.reply_text(
            m(user.id, "savol_matni", joriy=joriy_yangi, jami=jami),
            parse_mode="Markdown",
            reply_markup=javob_tugmalari()
        )
        return SAVOL_KUTILMOQDA


async def tasdiq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import json as _json
    query   = update.callback_query
    await query.answer()
    user    = query.from_user
    uid_str = str(user.id)
    test    = joriy_test_olish()

    if query.data == "tasdiq_yoq":
        context.user_data["joriy_savol"]         = 1
        context.user_data["kiritilgan_javoblar"] = {}
        await query.edit_message_text(m(user.id, "qaytadan"))
        if test:
            jami = len(togri_javoblar_parse(test))
            await query.message.reply_text(
                m(user.id, "savol_matni", joriy=1, jami=jami),
                parse_mode="Markdown",
                reply_markup=javob_tugmalari()
            )
        return SAVOL_KUTILMOQDA

    if not test:
        await query.edit_message_text("❌ Test topilmadi.")
        return JAVOB_KUTILMOQDA

    # Vaqt tekshiruvi
    if uid_str in _faol_taymerlar:
        boshlangan   = _faol_taymerlar[uid_str]
        utgan_daqiqa = (datetime.now(timezone.utc) - boshlangan).total_seconds() / 60
        if utgan_daqiqa >= test["vaqt_daqiqa"]:
            await nol_ball_saqlash(user.id, context.bot)
            await query.edit_message_text(m(user.id, "vaqt_tugadi"))
            context.user_data.clear()
            return JAVOB_KUTILMOQDA

    if test["holat"] != "ochiq":
        await query.edit_message_text(m(user.id, "test_ochiq_emas"))
        context.user_data.clear()
        return JAVOB_KUTILMOQDA

    test_id = test["id"]
    if natija_bormi(user.id, test_id):
        n = natija_bormi(user.id, test_id)
        await query.edit_message_text(
            m(user.id, "allaqachon_topshirdi",
              foiz=n["foiz"], togri=n["togri"],
              jami=n["jami"], vaqt=n["vaqt"]),
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return JAVOB_KUTILMOQDA

    await query.edit_message_text("⏳ Natijalar hisoblanmoqda...")

    foydalanuvchi_javoblari = context.user_data.get("kiritilgan_javoblar", {})
    togri_j = togri_javoblar_parse(test)
    togri, xato, topilmagan, foiz, savol_natijalari = javoblarni_tekshir(
        foydalanuvchi_javoblari, togri_j
    )
    jami = len(togri_j)

    with db_ulanish() as conn:
        conn.execute("""
            INSERT INTO natijalar
            (user_id, test_id, ism, username, togri, xato, topilmagan,
             jami, foiz, savol_natijalari, vaqt, vaqt_tugadi)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,0)
        """, (uid_str, test_id,
              user.first_name or "—",
              f"@{user.username}" if user.username else "—",
              togri, xato, topilmagan, jami, foiz,
              _json.dumps({str(k): v for k, v in savol_natijalari.items()}),
              hozirgi_vaqt()))

    taymer_bekor_qilish(user.id, context)

    orn, jami_ish = joriy_orn(user.id, test_id)
    emoji         = "✅" if foiz >= OTISH_BALI else "❌"
    holat_soz     = m(user.id, "otdi") if foiz >= OTISH_BALI else m(user.id, "otmadi")
    intriga       = intriga_xabar(user.id, orn, jami_ish)

    await query.message.reply_text(
        f"📊 *{test['nomi']} — Natijangiz*\n"
        f"{'─'*28}\n"
        f"✅ To'g'ri: *{togri}/{jami}*\n"
        f"❌ Xato: *{xato}*\n"
        f"⬜ Javob yo'q: *{topilmagan}*\n"
        f"📈 Foiz: *{foiz}%*\n"
        f"{emoji} *{holat_soz}!*\n"
        f"🏅 O'rningiz: *{orn}/{jami_ish}*\n"
        f"{'─'*28}\n\n{intriga}",
        parse_mode="Markdown",
        reply_markup=foydalanuvchi_tugmalari(user.id)
    )

    # Taqqoslama tahlil yuborish
    await taqqoslama_yuborish(update, context, user.id, test["nomi"], foiz)

    context.user_data.clear()
    return JAVOB_KUTILMOQDA


async def taqqoslama_yuborish(update, context, user_id: int, test_nomi: str, foiz: float):
    """Har test yakunida o'quvchiga taqqoslama tahlil yuboradi."""
    with db_ulanish() as conn:
        rows = conn.execute("""
            SELECT foiz FROM natijalar
            WHERE user_id=?
            ORDER BY id ASC
        """, (str(user_id),)).fetchall()

    if len(rows) < 2:
        return

    foizlar  = [r["foiz"] for r in rows]
    ortacha  = round(sum(foizlar) / len(foizlar), 1)
    oxirgi   = foizlar[-1]
    oldingi  = foizlar[-2]
    fark     = round(abs(oxirgi - oldingi), 1)

    if oxirgi > oldingi:
        dinamika = m(user_id, "osish", fark=fark)
    elif oxirgi < oldingi:
        dinamika = m(user_id, "tushish", fark=fark)
    else:
        dinamika = m(user_id, "barqaror")

    xulosa = m(user_id, "ajoyib") if ortacha >= OTISH_BALI else m(user_id, "davom_eting")

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=m(user_id, "taqqoslama",
                   test_nomi=test_nomi, foiz=foiz,
                   ortacha=ortacha, dinamika=dinamika, xulosa=xulosa),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Taqqoslama yuborishda xatolik: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 📖 MANBALAR ARXIVI
# ─────────────────────────────────────────────────────────────────────────────

async def manbalar_korsatish(update: Update, context: ContextTypes.DEFAULT_TYPE, sahifa: int = 1):
    user = update.effective_user
    with db_ulanish() as conn:
        jami = conn.execute("SELECT COUNT(*) as c FROM manbalar").fetchone()["c"]
        rows = conn.execute(
            "SELECT * FROM manbalar ORDER BY id LIMIT ? OFFSET ?",
            (SAHIFA_HAJMI, (sahifa - 1) * SAHIFA_HAJMI)
        ).fetchall()

    if jami == 0:
        await update.message.reply_text(m(user.id, "manbalar_yoq"))
        return

    jami_sahifa = (jami + SAHIFA_HAJMI - 1) // SAHIFA_HAJMI
    boshlang    = (sahifa - 1) * SAHIFA_HAJMI + 1
    oxiri       = min(sahifa * SAHIFA_HAJMI, jami)

    matn = m(user.id, "manbalar_sarlavha", joriy=boshlang, oxiri=oxiri, jami=jami)
    for i, r in enumerate(rows, boshlang):
        matn += f"{i}. {r['nomi']}\n"
    matn += m(user.id, "manbalar_tanla")

    context.user_data["manbalar_sahifa"] = sahifa
    context.user_data["manbalar_boshlang"] = boshlang

    await update.message.reply_text(
        matn,
        parse_mode="Markdown",
        reply_markup=manbalar_sahifa_tugmalari(user.id, sahifa, jami_sahifa)
    )


async def manbalar_sahifa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user

    if query.data == "manba_sahifa_info":
        return JAVOB_KUTILMOQDA

    sahifa = int(query.data.split("_")[-1])
    with db_ulanish() as conn:
        jami = conn.execute("SELECT COUNT(*) as c FROM manbalar").fetchone()["c"]
        rows = conn.execute(
            "SELECT * FROM manbalar ORDER BY id LIMIT ? OFFSET ?",
            (SAHIFA_HAJMI, (sahifa - 1) * SAHIFA_HAJMI)
        ).fetchall()

    jami_sahifa = (jami + SAHIFA_HAJMI - 1) // SAHIFA_HAJMI
    boshlang    = (sahifa - 1) * SAHIFA_HAJMI + 1
    oxiri       = min(sahifa * SAHIFA_HAJMI, jami)

    matn = m(user.id, "manbalar_sarlavha", joriy=boshlang, oxiri=oxiri, jami=jami)
    for i, r in enumerate(rows, boshlang):
        matn += f"{i}. {r['nomi']}\n"
    matn += m(user.id, "manbalar_tanla")

    context.user_data["manbalar_sahifa"] = sahifa
    context.user_data["manbalar_boshlang"] = boshlang

    await query.edit_message_text(
        matn,
        parse_mode="Markdown",
        reply_markup=manbalar_sahifa_tugmalari(user.id, sahifa, jami_sahifa)
    )
    return JAVOB_KUTILMOQDA


async def manba_raqam_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi manba raqamini kiritganda fayl yuboradi."""
    user = update.effective_user
    matn = update.message.text.strip()

    if not matn.isdigit():
        return JAVOB_KUTILMOQDA

    raqam = int(matn)
    with db_ulanish() as conn:
        rows = conn.execute(
            "SELECT * FROM manbalar ORDER BY id"
        ).fetchall()

    if raqam < 1 or raqam > len(rows):
        await update.message.reply_text(m(user.id, "manba_yoq"))
        return JAVOB_KUTILMOQDA

    manba = rows[raqam - 1]
    try:
        if manba["fayl_turi"] == "pdf":
            await context.bot.send_document(
                chat_id=user.id,
                document=manba["file_id"],
                caption=f"📄 *{manba['nomi']}*",
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_document(
                chat_id=user.id,
                document=manba["file_id"],
                caption=f"📁 *{manba['nomi']}*",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Manba yuborishda xatolik: {e}")
        await update.message.reply_text("❌ Fayl yuborishda xatolik yuz berdi.")

    return JAVOB_KUTILMOQDA


# ─────────────────────────────────────────────────────────────────────────────
# ⚙️ SOZLAMALAR
# ─────────────────────────────────────────────────────────────────────────────

async def sozlamalar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user

    if query.data == "sozlama_til":
        til_nomi = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
        joriy_til = foydalanuvchi_tili(user.id)
        await query.edit_message_text(
            f"🌐 Tilni tanlang / Выберите язык / Choose language:\n\n"
            f"Hozirgi til: {til_nomi.get(joriy_til, joriy_til)}",
            reply_markup=til_tugmalari(sozlama=True)
        )
        return JAVOB_KUTILMOQDA

    return JAVOB_KUTILMOQDA


async def til_ozgartirish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user  = query.from_user
    # sozlama_til_uz → uz
    til   = query.data.split("_")[-1]

    with db_ulanish() as conn:
        conn.execute(
            "UPDATE foydalanuvchilar SET til=? WHERE user_id=?",
            (til, str(user.id))
        )

    til_nomi = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}.get(til)
    await query.edit_message_text(f"✅ Til o'zgartirildi: {til_nomi}")
    await query.message.reply_text(
        m(user.id, "xush_kelibsiz"),
        reply_markup=foydalanuvchi_tugmalari(user.id)
    )
    return JAVOB_KUTILMOQDA


# ─────────────────────────────────────────────────────────────────────────────
# 👤 ADMIN — PDF VA MANBA
# ─────────────────────────────────────────────────────────────────────────────

async def pdf_qabul_qil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    fayl = update.message.document
    test = joriy_test_olish()
    if not test:
        await update.message.reply_text(
            "⚠️ Avval test yarating (Kalit o'zgartirish orqali).",
            reply_markup=admin_tugmalari()
        )
        return
    with db_ulanish() as conn:
        conn.execute(
            "UPDATE testlar SET pdf_file_id=? WHERE id=?",
            (fayl.file_id, test["id"])
        )
    await update.message.reply_text(
        f"✅ *Test fayli saqlandi!*\n📄 {fayl.file_name}",
        parse_mode="Markdown",
        reply_markup=admin_tugmalari()
    )


async def manba_qoshish_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA
    await update.message.reply_text(
        "📖 *Manba qo'shish*\n\nFayl (PDF yoki Word) yuboring:\n\nBekor qilish: /bekor",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return MANBA_NOM_KUTILMOQDA


async def manba_fayl_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA
    if not update.message.document:
        await update.message.reply_text("❌ Fayl yuboring (PDF yoki Word).")
        return MANBA_NOM_KUTILMOQDA

    fayl = update.message.document
    fayl_turi = "pdf" if "pdf" in (fayl.mime_type or "") else "word"
    context.user_data["yangi_manba"] = {
        "file_id"  : fayl.file_id,
        "fayl_turi": fayl_turi,
        "fayl_nomi": fayl.file_name
    }
    await update.message.reply_text(
        f"✅ Fayl qabul qilindi: `{fayl.file_name}`\n\nBu faylga *nom* bering:",
        parse_mode="Markdown"
    )
    return MANBA_NOM_KUTILMOQDA


async def manba_nom_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA

    if "yangi_manba" not in context.user_data:
        await update.message.reply_text("❌ Avval fayl yuboring.")
        return MANBA_NOM_KUTILMOQDA

    nom  = update.message.text.strip()
    m_d  = context.user_data["yangi_manba"]

    with db_ulanish() as conn:
        conn.execute(
            "INSERT INTO manbalar (nomi, file_id, fayl_turi, qoshilgan) VALUES (?,?,?,?)",
            (nom, m_d["file_id"], m_d["fayl_turi"], hozirgi_vaqt())
        )
        jami = conn.execute("SELECT COUNT(*) as c FROM manbalar").fetchone()["c"]

    context.user_data.pop("yangi_manba", None)
    await update.message.reply_text(
        f"✅ *Manba qo'shildi!*\n\n📄 Nom: *{nom}*\n📚 Jami manbalar: *{jami}* ta",
        parse_mode="Markdown",
        reply_markup=admin_tugmalari()
    )
    return ConversationHandler.END


async def manba_ochirish_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA

    with db_ulanish() as conn:
        rows = conn.execute("SELECT * FROM manbalar ORDER BY id").fetchall()

    if not rows:
        await update.message.reply_text("📭 Manbalar ro'yxati bo'sh.")
        return JAVOB_KUTILMOQDA

    matn = "🗑 *Qaysi manbani o'chirmoqchisiz?*\n\nRaqamini yuboring:\n\n"
    for i, r in enumerate(rows, 1):
        matn += f"{i}. {r['nomi']}\n"
    matn += "\nBekor qilish: /bekor"

    await update.message.reply_text(
        matn, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove()
    )
    return MANBA_OCHIR_KUTILMOQDA


async def manba_ochirish_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA

    matn = update.message.text.strip()
    with db_ulanish() as conn:
        rows = conn.execute("SELECT * FROM manbalar ORDER BY id").fetchall()

    if not matn.isdigit() or int(matn) < 1 or int(matn) > len(rows):
        await update.message.reply_text("❌ Noto'g'ri raqam. Qaytadan kiriting.")
        return MANBA_OCHIR_KUTILMOQDA

    manba = rows[int(matn) - 1]
    with db_ulanish() as conn:
        conn.execute("DELETE FROM manbalar WHERE id=?", (manba["id"],))

    await update.message.reply_text(
        f"✅ *{manba['nomi']}* o'chirildi!",
        parse_mode="Markdown",
        reply_markup=admin_tugmalari()
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────
# 👤 ADMIN — TEST BOSHQARUVI
# ─────────────────────────────────────────────────────────────────────────────

async def vaqt_sorash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA
    test = joriy_test_olish()
    if not test or not test["pdf_file_id"]:
        await update.message.reply_text(
            "⚠️ Avval:\n1. Kalit o'zgartiring\n2. PDF faylni yuboring",
            reply_markup=admin_tugmalari()
        )
        return JAVOB_KUTILMOQDA
    await update.message.reply_text(
        f"⏱ *Test vaqtini kiriting*\n\nNecha daqiqa? (kamida 11)\n\nBekor: /bekor",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return VAQT_KUTILMOQDA


async def vaqt_qabul_qil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = update.message.text.strip()
    if not matn.isdigit() or int(matn) <= 10:
        await update.message.reply_text(
            "❌ Kamida 11 daqiqa kiriting.\n\nBekor: /bekor"
        )
        return VAQT_KUTILMOQDA

    daqiqa = int(matn)
    test   = joriy_test_olish()
    with db_ulanish() as conn:
        conn.execute(
            "UPDATE testlar SET vaqt_daqiqa=?, holat='ochiq', yaratilgan=? WHERE id=?",
            (daqiqa, hozirgi_vaqt(), test["id"])
        )

    # Kanalga avtomatik xabar
    try:
        await context.bot.send_message(
            chat_id=KANAL_ID,
            text=(
                f"🟢 *Test boshlandi!*\n\n"
                f"📝 {test['nomi']}\n"
                f"⏱ Vaqt: *{daqiqa}* daqiqa\n\n"
                f"Botga kiring va testni boshlang! 👇"
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Kanalga xabar yuborishda xatolik: {e}")

    await update.message.reply_text(
        f"▶️ *{test['nomi']}* boshlandi!\n⏱ {daqiqa} daqiqa",
        parse_mode="Markdown",
        reply_markup=admin_tugmalari()
    )
    return ConversationHandler.END


async def test_yakunlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    test = joriy_test_olish()
    if not test:
        await update.message.reply_text("❌ Faol test topilmadi.")
        return

    with db_ulanish() as conn:
        conn.execute(
            "UPDATE testlar SET holat='yopiq', yakunlangan=? WHERE id=?",
            (hozirgi_vaqt(), test["id"])
        )

    # Faol taymerlarni yopish
    nol_saqlangan = 0
    for uid_str in list(_faol_taymerlar.keys()):
        for nom in [f"ogohlantirish_{uid_str}", f"vaqt_tugadi_{uid_str}"]:
            for job in context.job_queue.get_jobs_by_name(nom):
                job.schedule_removal()
        if not natija_bormi(int(uid_str), test["id"]):
            await nol_ball_saqlash(int(uid_str), context.bot)
            nol_saqlangan += 1

    with db_ulanish() as conn:
        jami = conn.execute(
            "SELECT COUNT(*) as c FROM natijalar WHERE test_id=?", (test["id"],)
        ).fetchone()["c"]

    await update.message.reply_text(
        f"⏹ *{test['nomi']}* yakunlandi!\n\n"
        f"👥 Jami ishtirokchi: *{jami}* ta\n"
        f"⏰ Vaqti tugib 0 ball: *{nol_saqlangan}* ta\n\n"
        f"Javoblarni kanalga e'lon qilish uchun 📢 *E'lon qilish* tugmasini bosing.",
        parse_mode="Markdown",
        reply_markup=admin_tugmalari()
    )


async def elon_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA
    test = joriy_test_olish()
    if not test:
        await update.message.reply_text("❌ Test topilmadi.")
        return JAVOB_KUTILMOQDA

    import json as _json
    togri_j = togri_javoblar_parse(test)
    preview = " ".join([f"{r}-{j}" for r, j in sorted(togri_j.items())])

    await update.message.reply_text(
        f"📢 *Kanalga e'lon qilish*\n\n"
        f"Test: *{test['nomi']}*\n\n"
        f"✅ *To'g'ri javoblar:*\n`{preview}`\n\n"
        f"Shu PDF va javoblar kanalga yuboriladimi?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 Ha, e'lon qilish", callback_data="kanal_elon_ha"),
            InlineKeyboardButton("❌ Bekor", callback_data="kanal_elon_yoq"),
        ]])
    )
    return KANAL_ELON_TASDIQ


async def kanal_elon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "kanal_elon_yoq":
        await query.edit_message_text("🚫 E'lon bekor qilindi.")
        return JAVOB_KUTILMOQDA

    test = joriy_test_olish()
    if not test:
        await query.edit_message_text("❌ Test topilmadi.")
        return JAVOB_KUTILMOQDA

    togri_j = togri_javoblar_parse(test)
    preview = " ".join([f"{r}-{j}" for r, j in sorted(togri_j.items())])

    try:
        # PDF yuborish
        if test["pdf_file_id"]:
            await context.bot.send_document(
                chat_id=KANAL_ID,
                document=test["pdf_file_id"],
                caption=f"📝 *{test['nomi']}* — Test savollari",
                parse_mode="Markdown"
            )
        # To'g'ri javoblar
        await context.bot.send_message(
            chat_id=KANAL_ID,
            text=(
                f"✅ *{test['nomi']} — To'g'ri javoblar:*\n\n"
                f"`{preview}`"
            ),
            parse_mode="Markdown"
        )
        await query.edit_message_text("✅ PDF va javoblar kanalga yuborildi!")
    except Exception as e:
        logger.error(f"Kanal e'lonida xatolik: {e}")
        await query.edit_message_text(f"❌ Xatolik: {e}")

    return JAVOB_KUTILMOQDA


async def kalit_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA
    await update.message.reply_text(
        "🔑 *Yangi test kaliti*\n\n"
        "Test nomini yuboring:\n\nBekor: /bekor",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return TESTNOM_KUTILMOQDA


async def testnom_boshlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return JAVOB_KUTILMOQDA
    await update.message.reply_text(
        "✏️ Yangi test nomini kiriting:\n\nBekor: /bekor",
        reply_markup=ReplyKeyboardRemove()
    )
    return TESTNOM_KUTILMOQDA


async def testnom_qabul_qil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nom = update.message.text.strip()
    context.user_data["yangi_test_nomi"] = nom
    await update.message.reply_text(
        f"✅ Test nomi: *{nom}*\n\n"
        f"Endi kalitni yuboring:\n`1A 2B 3C 4D ...`\n\nBekor: /bekor",
        parse_mode="Markdown"
    )
    return KALIT_KUTILMOQDA


async def kalit_qabul_qil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import json as _json
    matn = update.message.text.strip()
    javoblar, xatolar = matnni_parse_qil(matn)

    if not javoblar:
        await update.message.reply_text(
            "❌ Kalit topilmadi.\nFormat: `1A 2B 3C`\n\nBekor: /bekor",
            parse_mode="Markdown"
        )
        return KALIT_KUTILMOQDA

    if xatolar:
        await update.message.reply_text(
            f"❌ Noto'g'ri qismlar: `{', '.join(xatolar)}`\n\nBekor: /bekor",
            parse_mode="Markdown"
        )
        return KALIT_KUTILMOQDA

    nom = context.user_data.get("yangi_test_nomi", "Yangi test")

    with db_ulanish() as conn:
        cursor = conn.execute("""
            INSERT INTO testlar (nomi, togri_javoblar, holat, yaratilgan)
            VALUES (?, ?, 'tayyorlanmoqda', ?)
        """, (nom, _json.dumps({str(k): v for k, v in javoblar.items()}), hozirgi_vaqt()))
        test_id = cursor.lastrowid
        conn.execute(
            "UPDATE sozlamalar SET qiymat=? WHERE kalit='joriy_test_id'",
            (str(test_id),)
        )

    preview = " ".join([f"{r}{j}" for r, j in sorted(javoblar.items())])
    await update.message.reply_text(
        f"✅ *Yangi test yaratildi!*\n\n"
        f"📝 Nom: *{nom}*\n"
        f"🔢 Savollar: *{len(javoblar)}* ta\n"
        f"🔑 Kalit: `{preview}`\n\n"
        f"Endi PDF faylini yuboring.",
        parse_mode="Markdown",
        reply_markup=admin_tugmalari()
    )
    context.user_data.pop("yangi_test_nomi", None)
    return ConversationHandler.END


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    test = joriy_test_olish()
    if not test:
        await update.message.reply_text("❌ Test topilmadi.")
        return

    for uid_str in list(_faol_taymerlar.keys()):
        try:
            uid = int(uid_str)
            for nom in [f"ogohlantirish_{uid}", f"vaqt_tugadi_{uid}"]:
                for job in context.job_queue.get_jobs_by_name(nom):
                    job.schedule_removal()
        except Exception:
            pass
    _faol_taymerlar.clear()

    with db_ulanish() as conn:
        jami = conn.execute(
            "SELECT COUNT(*) as c FROM natijalar WHERE test_id=?", (test["id"],)
        ).fetchone()["c"]
        conn.execute("DELETE FROM natijalar WHERE test_id=?", (test["id"],))

    await update.message.reply_text(
        f"🔄 *Natijalar tozalandi!*\n\nO'chirilgan: *{jami}* ta",
        parse_mode="Markdown",
        reply_markup=admin_tugmalari()
    )


# ─────────────────────────────────────────────────────────────────────────────
# 📊 ADMIN STATISTIKA
# ─────────────────────────────────────────────────────────────────────────────

async def statistika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    test = joriy_test_olish()
    if not test:
        await update.message.reply_text("❌ Test topilmadi.")
        return

    with db_ulanish() as conn:
        rows = conn.execute(
            "SELECT * FROM natijalar WHERE test_id=? ORDER BY foiz DESC",
            (test["id"],)
        ).fetchall()

    if not rows:
        await update.message.reply_text("📭 Hali hech kim test topshirmagan.")
        return

    jami      = len(rows)
    foizlar   = [r["foiz"] for r in rows]
    otganlar  = [r for r in rows if r["foiz"] >= OTISH_BALI]
    ortacha   = round(sum(foizlar) / jami, 1)
    mediana   = round(stats_lib.median(foizlar), 1)
    eng_yuqori= max(foizlar)
    eng_past  = min(foizlar)
    vaqt_tugdi= sum(1 for r in rows if r["vaqt_tugadi"])
    otmagan   = jami - len(otganlar)

    umumiy = (
        f"📊 *{test['nomi']} — Statistika*\n{'─'*30}\n"
        f"👥 Jami: *{jami}*\n"
        f"✅ O'tganlar: *{len(otganlar)}*\n"
        f"❌ O'tmaganlar: *{otmagan}*\n"
        f"   ↳ Vaqti tugaganlar: *{vaqt_tugdi}*\n"
        f"{'─'*30}\n"
        f"📈 O'rtacha: *{ortacha}%*\n"
        f"📊 Mediana: *{mediana}%*\n"
        f"🏆 Eng yuqori: *{eng_yuqori}%*\n"
        f"📉 Eng past: *{eng_past}%*\n"
    )
    await update.message.reply_text(umumiy, parse_mode="Markdown")

    # Savol tahlili
    import json as _json
    togri_j    = togri_javoblar_parse(test)
    savol_stat = {}
    for r in rows:
        try:
            sn = _json.loads(r["savol_natijalari"])
        except Exception:
            continue
        for raqam_str, natija in sn.items():
            raqam = int(raqam_str)
            if raqam not in savol_stat:
                savol_stat[raqam] = {"togri": 0, "xato": 0, "topilmagan": 0}
            savol_stat[raqam][natija] = savol_stat[raqam].get(natija, 0) + 1

    saralangan = sorted(savol_stat.items(), key=lambda x: x[1]["xato"], reverse=True)
    savol_matn = f"📋 *Savol tahlili ({len(togri_j)} ta):*\n{'─'*30}\n"
    for raqam, st in saralangan:
        togri_javob  = togri_j.get(raqam, "?")
        togri_f      = round(st["togri"] / jami * 100, 1)
        xato_f       = round(st["xato"] / jami * 100, 1)
        topilmagan_f = round(st["topilmagan"] / jami * 100, 1)
        savol_matn  += (
            f"❓ *{raqam}-savol* (to'g'ri: `{togri_javob}`)\n"
            f"   ✅{st['togri']}({togri_f}%) ❌{st['xato']}({xato_f}%) ⬜{st['topilmagan']}({topilmagan_f}%)\n"
        )
    await xabar_yuborish_chunks(update, savol_matn)

    # Reyting
    medallar = {1: "🥇", 2: "🥈", 3: "🥉"}
    sarlavha = f"🏆 *Reyting ({jami} nafar):*\n{'─'*30}\n"
    qatorlar = []
    for i, r in enumerate(rows, 1):
        medal = medallar.get(i, f"{i}.")
        emoji = "✅" if r["foiz"] >= OTISH_BALI else "❌"
        vt    = " ⏰" if r["vaqt_tugadi"] else ""
        qatorlar.append(
            f"{medal} {r['ism']} ({r['username']}){vt}\n"
            f"   {emoji} {r['foiz']}% | ✅{r['togri']}/❌{r['xato']}/⬜{r['topilmagan']}"
        )
    await xabar_yuborish_chunks(update, sarlavha + "\n".join(qatorlar))


async def foydalanuvchilar_statistikasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    with db_ulanish() as conn:
        jami = conn.execute(
            "SELECT COUNT(*) as c FROM foydalanuvchilar WHERE royxatdan=1"
        ).fetchone()["c"]

        tumanlar = conn.execute("""
            SELECT tuman, COUNT(*) as c FROM foydalanuvchilar
            WHERE royxatdan=1 GROUP BY tuman ORDER BY c DESC LIMIT 10
        """).fetchall()

        sinflar = conn.execute("""
            SELECT sinf, COUNT(*) as c FROM foydalanuvchilar
            WHERE royxatdan=1 GROUP BY sinf ORDER BY c DESC LIMIT 10
        """).fetchall()

        yoshlar = conn.execute("""
            SELECT yosh, COUNT(*) as c FROM foydalanuvchilar
            WHERE royxatdan=1 GROUP BY yosh ORDER BY yosh
        """).fetchall()

        tillar = conn.execute("""
            SELECT til, COUNT(*) as c FROM foydalanuvchilar
            WHERE royxatdan=1 GROUP BY til
        """).fetchall()

    til_nomi = {"uz": "🇺🇿 O'zbek", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}

    matn = (
        f"👥 *Foydalanuvchilar statistikasi*\n{'─'*30}\n"
        f"Jami ro'yxatdan o'tganlar: *{jami}* ta\n\n"
        f"🏘 *Tumanlar (TOP-10):*\n"
    )
    for r in tumanlar:
        matn += f"  • {r['tuman'] or '—'}: *{r['c']}* ta\n"

    matn += f"\n📚 *Sinflar (TOP-10):*\n"
    for r in sinflar:
        matn += f"  • {r['sinf'] or '—'}: *{r['c']}* ta\n"

    matn += f"\n🎂 *Yoshlar:*\n"
    for r in yoshlar:
        matn += f"  • {r['yosh']} yosh: *{r['c']}* ta\n"

    matn += f"\n🌐 *Tillar:*\n"
    for r in tillar:
        matn += f"  • {til_nomi.get(r['til'], r['til'])}: *{r['c']}* ta\n"

    await xabar_yuborish_chunks(update, matn)


async def holat_korsatish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    test = joriy_test_olish()
    if not test:
        await update.message.reply_text("❌ Hozircha test yo'q.")
        return

    togri_j = togri_javoblar_parse(test)
    holat_soz = {"ochiq": "✅ Ochiq", "yopiq": "⏹ Yopiq", "tayyorlanmoqda": "🔧 Tayyorlanmoqda"}.get(
        test["holat"], test["holat"]
    )

    satrlar = [
        f"📋 *{test['nomi']} — Joriy holat:*\n",
        f"Holat: *{holat_soz}*",
        f"⏱ Vaqt: *{test['vaqt_daqiqa']}* daqiqa",
        f"⏳ Faol taymerlar: *{len(_faol_taymerlar)}* ta\n",
        f"*Kalit ({len(togri_j)} ta savol):*",
    ]
    for raqam in sorted(togri_j.keys()):
        satrlar.append(f"{raqam}. {togri_j[raqam]}")
    satrlar.append(f"\n📊 O'tish bali: *{OTISH_BALI}%*")
    await update.message.reply_text("\n".join(satrlar), parse_mode="Markdown")



# ─────────────────────────────────────────────────────────────────────────────
# 🧪 AI XIMIK
# ─────────────────────────────────────────────────────────────────────────────

async def ai_ximik_boshlash(update, context):
    """Foydalanuvchi 🧪 AI Ximik / 🧪 AI Maslahat tugmasini bosganda."""
    user = update.effective_user

    # Suhbat tarixini tozalash
    context.user_data["ai_tarix"]      = []
    context.user_data["ai_xabar_soni"] = 0

    # Admin uchun maslahat rejimi
    if user.id == ADMIN_ID:
        profil = profil_olish(user.id)
        profil["suhbat_soni"] = profil.get("suhbat_soni", 0) + 1
        profil_saqlash(user.id, profil)
        await update.message.reply_text(
            "🧪 *AI Maslahat* — Ustoz rejimi\n\n"
            "O\'quvchilar haqida savol bering yoki umumiy tahlil so\'rang.\n\n"
            "_Chiqish uchun 🚪 tugmasini bosing._",
            parse_mode="Markdown",
            reply_markup=ai_tugmasi(user.id)
        )
        return AI_SUHBAT

    # O\'quvchi uchun limit tekshiruvi
    ruxsat, qolgan = limit_tekshir(user.id)
    if not ruxsat:
        await update.message.reply_text(
            m(user.id, "ai_limit", limit=KUNLIK_LIMIT),
            parse_mode="Markdown",
            reply_markup=foydalanuvchi_tugmalari(user.id)
        )
        return JAVOB_KUTILMOQDA

    # Profilni yangilash
    profil = profil_olish(user.id)
    profil["suhbat_soni"] = profil.get("suhbat_soni", 0) + 1
    profil_saqlash(user.id, profil)

    await update.message.reply_text(
        m(user.id, "ai_xush_keldi"),
        parse_mode="Markdown",
        reply_markup=ai_tugmasi(user.id)
    )
    return AI_SUHBAT


async def ai_suhbat(update, context):
    """AI suhbat holatida xabarlarni qabul qiladi."""
    user = update.effective_user
    matn = update.message.text.strip()

    # Chiqish tugmasi matnlari
    chiqish_matnlar = ["🚪 AI dan chiqish", "🚪 Выйти из AI", "🚪 Exit AI"]
    if matn in chiqish_matnlar:
        # Suhbat oxirida profil yangilash
        tarix = context.user_data.get("ai_tarix", [])
        if tarix:
            import threading
            suhbat_matni = "\n".join([x["role"] + ": " + x["content"] for x in tarix])
            threading.Thread(
                target=profil_yangilash_ai,
                args=(user.id, suhbat_matni),
                daemon=True
            ).start()

        context.user_data["ai_tarix"]      = []
        context.user_data["ai_xabar_soni"] = 0

        if user.id == ADMIN_ID:
            await update.message.reply_text(
                "🚪 AI Maslahat yakunlandi.",
                reply_markup=admin_tugmalari()
            )
        else:
            await update.message.reply_text(
                "🚪 AI Ximikdan chiqdingiz. Muvaffaqiyatli o\'qishlar! 📚",
                reply_markup=foydalanuvchi_tugmalari(user.id)
            )
        return JAVOB_KUTILMOQDA

    # O\'quvchi uchun limit tekshiruvi
    if user.id != ADMIN_ID:
        ruxsat, qolgan = limit_tekshir(user.id)
        if not ruxsat:
            await update.message.reply_text(
                m(user.id, "ai_limit", limit=KUNLIK_LIMIT),
                parse_mode="Markdown",
                reply_markup=foydalanuvchi_tugmalari(user.id)
            )
            return JAVOB_KUTILMOQDA

    # "Yozmoqda..." ko\'rsatish
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )

    tarix = context.user_data.get("ai_tarix", [])

    # AI javob olish
    muvaffaqiyatli = False
    try:
        if user.id == ADMIN_ID:
            javob = await admin_ai_javob(matn, tarix)
        else:
            javob = await ai_javob_olish(user.id, matn, tarix)
        muvaffaqiyatli = True
    except Exception:
        javob = "❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko\'ring."

    # Faqat muvaffaqiyatli javobda tarix, limit va profil yangilanadi
    if muvaffaqiyatli:
        # Tarixni yangilash (oxirgi 20 xabar)
        tarix.append({"role": "user",      "content": matn})
        tarix.append({"role": "assistant", "content": javob})
        context.user_data["ai_tarix"] = tarix[-20:]

        # O\'quvchi uchun limit va profil
        if user.id != ADMIN_ID:
            limit_oshir(user.id)
            xabar_soni = context.user_data.get("ai_xabar_soni", 0) + 1
            context.user_data["ai_xabar_soni"] = xabar_soni

            # Har 5 xabardan keyin profil yangilash (thread da — bot bloklanmasin)
            if xabar_soni % 5 == 0:
                import threading
                suhbat_matni = "\n".join([x["role"] + ": " + x["content"] for x in tarix])
                threading.Thread(
                    target=profil_yangilash_ai,
                    args=(user.id, suhbat_matni),
                    daemon=True
                ).start()

            # Limit eslatmasi (5 ta va kamroq qolganda)
            _, qolgan = limit_tekshir(user.id)
            if qolgan <= 5:
                javob += f"\n\n_💬 Bugun yana {qolgan} ta savol bera olasiz_"

    # Javobni yuborish (Markdown xatosiz)
    try:
        await update.message.reply_text(
            javob,
            parse_mode="Markdown",
            reply_markup=ai_tugmasi(user.id)
        )
    except Exception:
        await update.message.reply_text(
            javob,
            reply_markup=ai_tugmasi(user.id)
        )
    return AI_SUHBAT


# ─────────────────────────────────────────────────────────────────────────────
# 📨 MUROJAAT
# ─────────────────────────────────────────────────────────────────────────────

async def murojaat_qabul_qil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    matn     = update.message.text.strip()
    ism      = user.first_name or "Noma'lum"
    username = f"@{user.username}" if user.username else "—"

    yuborilgan = await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"📨 *Yangi murojaat*\n{'─'*28}\n"
            f"👤 {ism} ({username})\n"
            f"🆔 `{user.id}`\n{'─'*28}\n"
            f"{matn}"
        ),
        parse_mode="Markdown"
    )

    with db_ulanish() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO murojaatlar (xabar_id, user_id) VALUES (?,?)",
            (str(yuborilgan.message_id), str(user.id))
        )

    await update.message.reply_text(
        m(user.id, "murojaat_yuborildi"),
        reply_markup=foydalanuvchi_tugmalari(user.id)
    )
    return JAVOB_KUTILMOQDA


async def admin_javob_qabul_qil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not update.message.reply_to_message:
        return

    reply_id = str(update.message.reply_to_message.message_id)
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT user_id FROM murojaatlar WHERE xabar_id=?", (reply_id,)
        ).fetchone()

    if not row:
        return

    foydalanuvchi_id = int(row["user_id"])
    javob = update.message.text.strip()

    try:
        await context.bot.send_message(
            chat_id=foydalanuvchi_id,
            text=f"📩 *Admin javob berdi:*\n{'─'*28}\n{javob}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Javob yuborildi!")
    except Exception as e:
        logger.error(f"Murojaat javobida xatolik: {e}")
        await update.message.reply_text("❌ Xabar yuborishda xatolik.")


# ─────────────────────────────────────────────────────────────────────────────
# 🔚 BEKOR
# ─────────────────────────────────────────────────────────────────────────────

async def bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    is_admin = user.id == ADMIN_ID
    context.user_data.clear()
    await update.message.reply_text(
        m(user.id, "bekor") if not is_admin else "🚫 Bekor qilindi.",
        reply_markup=admin_tugmalari() if is_admin else foydalanuvchi_tugmalari(user.id)
    )
    return ConversationHandler.END


async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user     = update.effective_user
    is_admin = user.id == ADMIN_ID
    if is_admin:
        await update.message.reply_text(
            "📖 *Admin yordam*\n\n"
            "1. Kalit o'zgartirish → Test nomi + kalit\n"
            "2. PDF yuboring\n"
            "3. Testni boshlash → Vaqt kiriting\n"
            "4. Testni yakunlash → Javoblarni e'lon qilish\n"
            "5. Manba qo'shish → Fayl + nom\n",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            m(user.id, "xush_kelibsiz"),
            reply_markup=foydalanuvchi_tugmalari(user.id)
        )


def token_tekshir():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN kiritilmagan!")


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    token_tekshir()
    DB_FAYL.parent.mkdir(exist_ok=True)
    db_yaratish()

    print("🤖 Bot-11 ishga tushmoqda...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    asosiy_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TIL_TANLASH          : [CallbackQueryHandler(til_callback, pattern="^til_(?!oz)")],
            ROYXAT_ISM           : [MessageHandler(filters.TEXT & ~filters.COMMAND, royxat_ism)],
            ROYXAT_TUMAN         : [MessageHandler(filters.TEXT & ~filters.COMMAND, royxat_tuman)],
            ROYXAT_MAKTAB        : [MessageHandler(filters.TEXT & ~filters.COMMAND, royxat_maktab)],
            ROYXAT_SINF          : [MessageHandler(filters.TEXT & ~filters.COMMAND, royxat_sinf)],
            ROYXAT_YOSH          : [MessageHandler(filters.TEXT & ~filters.COMMAND, royxat_yosh)],
            ROYXAT_KONTAKT       : [MessageHandler(filters.CONTACT, royxat_kontakt)],
            ROYXAT_TASDIQ        : [CallbackQueryHandler(royxat_tasdiq_callback, pattern="^royxat_tasdiq_")],
            JAVOB_KUTILMOQDA     : [
                MessageHandler(filters.TEXT & ~filters.COMMAND, javob_qabul_qil),
                CallbackQueryHandler(manbalar_sahifa_callback, pattern="^manba_sahifa_"),
                CallbackQueryHandler(obuna_tekshir_callback, pattern="^obuna_tekshir$"),
                CallbackQueryHandler(sozlamalar_callback, pattern="^sozlama_til$"),
                CallbackQueryHandler(til_ozgartirish_callback, pattern="^sozlama_til_"),
                CallbackQueryHandler(kanal_elon_callback, pattern="^kanal_elon_"),
            ],
            KALIT_KUTILMOQDA     : [MessageHandler(filters.TEXT & ~filters.COMMAND, kalit_qabul_qil)],
            TESTNOM_KUTILMOQDA   : [MessageHandler(filters.TEXT & ~filters.COMMAND, testnom_qabul_qil)],
            MUROJAAT_KUTILMOQDA  : [MessageHandler(filters.TEXT & ~filters.COMMAND, murojaat_qabul_qil)],
            VAQT_KUTILMOQDA      : [MessageHandler(filters.TEXT & ~filters.COMMAND, vaqt_qabul_qil)],
            SAVOL_KUTILMOQDA     : [CallbackQueryHandler(savol_callback, pattern="^javob_")],
            TASDIQ_KUTILMOQDA    : [CallbackQueryHandler(tasdiq_callback, pattern="^tasdiq_")],
            MANBA_NOM_KUTILMOQDA : [
                MessageHandler(filters.Document.ALL, manba_fayl_qabul),
                MessageHandler(filters.TEXT & ~filters.COMMAND, manba_nom_qabul),
            ],
            MANBA_OCHIR_KUTILMOQDA: [MessageHandler(filters.TEXT & ~filters.COMMAND, manba_ochirish_qabul)],
            KANAL_ELON_TASDIQ    : [CallbackQueryHandler(kanal_elon_callback, pattern="^kanal_elon_")],
            AI_SUHBAT            : [MessageHandler(filters.TEXT & ~filters.COMMAND, ai_suhbat)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("bekor", bekor),
            CommandHandler("yordam", yordam),
        ],
        per_message=False,
        per_chat=True,
        per_user=True,
    )

    # Admin reply handleri
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID) & filters.REPLY,
        admin_javob_qabul_qil
    ), group=0)

    # Admin PDF handleri
    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.User(ADMIN_ID),
        pdf_qabul_qil
    ), group=0)

    app.add_handler(asosiy_conv, group=1)
    app.add_handler(CommandHandler("yordam", yordam), group=1)

    print("✅ Bot-11 muvaffaqiyatli ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()

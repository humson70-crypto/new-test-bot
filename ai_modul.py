"""
AI Ximik moduli
- Foydalanuvchi profili (SQLite)
- Kunlik limit (20 xabar)
- Gemini API bilan suhbat
- Admin uchun cheksiz + o'quvchilar tahlili
"""

import os
import re
import json
import sqlite3
import httpx
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# SOZLAMALAR
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.0-flash-lite"
ADMIN_ID       = int(os.environ.get("ADMIN_ID", "7710339509"))
KUNLIK_LIMIT   = 20
DB_FAYL        = Path("data/bot.db")
UZ_TZ          = timezone(timedelta(hours=5))

# ─────────────────────────────────────────────────────────────────────────────
# MA'LUMOTLAR BAZASI
# ─────────────────────────────────────────────────────────────────────────────

def db_ulanish():
    DB_FAYL.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FAYL)
    conn.row_factory = sqlite3.Row
    return conn


def ai_jadvallar_yaratish():
    with db_ulanish() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ai_profil (
                user_id         TEXT PRIMARY KEY,
                daraja          TEXT DEFAULT 'noaniq',
                kuchli_tomonlar TEXT DEFAULT '[]',
                zaif_tomonlar   TEXT DEFAULT '[]',
                uslub           TEXT DEFAULT 'ortacha',
                suhbat_soni     INTEGER DEFAULT 0,
                xabar_soni      INTEGER DEFAULT 0,
                oxirgi_faollik  TEXT,
                yaratilgan      TEXT
            );
            CREATE TABLE IF NOT EXISTS ai_limit (
                user_id    TEXT,
                sana       TEXT,
                xabar_soni INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, sana)
            );
        """)

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI API
# ─────────────────────────────────────────────────────────────────────────────

def _json_tozala(matn: str) -> str:
    """Gemini markdown javobidan JSON ni tozalaydi."""
    return re.sub(r"```json|```", "", matn).strip()


async def _gemini_sorov(body: dict) -> str:
    """Gemini API ga async so'rov yuboradi — event loop bloklanmaydi."""
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY o'rnatilmagan!")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.HTTPStatusError as e:
            raise Exception(f"Gemini API xatolik: HTTP {e.response.status_code}")
        except httpx.TimeoutException:
            raise Exception("Gemini API javob bermadi (timeout)")
        except (KeyError, IndexError):
            raise Exception("Gemini API noto'g'ri javob qaytardi")
        except Exception:
            raise Exception("Gemini API bilan bog'lanishda xatolik")


async def _gemini_api_chaqir(system: str, user_msg: str, max_tokens: int = 300) -> str:
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents"          : [{"role": "user", "parts": [{"text": user_msg}]}],
        "generationConfig"  : {"maxOutputTokens": max_tokens},
    }
    return await _gemini_sorov(body)


async def _gemini_suhbat(system: str, messages: list, max_tokens: int = 800) -> str:
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents"          : messages,
        "generationConfig"  : {"maxOutputTokens": max_tokens},
    }
    return await _gemini_sorov(body)

# ─────────────────────────────────────────────────────────────────────────────
# PROFIL BOSHQARUV
# ─────────────────────────────────────────────────────────────────────────────

def profil_olish(user_id: int) -> dict:
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT * FROM ai_profil WHERE user_id=?", (str(user_id),)
        ).fetchone()
    if row:
        return {
            "daraja"         : row["daraja"],
            "kuchli_tomonlar": json.loads(row["kuchli_tomonlar"]),
            "zaif_tomonlar"  : json.loads(row["zaif_tomonlar"]),
            "uslub"          : row["uslub"],
            "suhbat_soni"    : row["suhbat_soni"],
            "xabar_soni"     : row["xabar_soni"],
            "oxirgi_faollik" : row["oxirgi_faollik"],
        }
    return {
        "daraja": "noaniq", "kuchli_tomonlar": [], "zaif_tomonlar": [],
        "uslub": "ortacha", "suhbat_soni": 0, "xabar_soni": 0, "oxirgi_faollik": None,
    }


def profil_saqlash(user_id: int, profil: dict):
    hozir = datetime.now(UZ_TZ).strftime("%d.%m.%Y %H:%M")
    with db_ulanish() as conn:
        conn.execute("""
            INSERT INTO ai_profil
                (user_id, daraja, kuchli_tomonlar, zaif_tomonlar,
                 uslub, suhbat_soni, xabar_soni, oxirgi_faollik, yaratilgan)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                daraja=excluded.daraja,
                kuchli_tomonlar=excluded.kuchli_tomonlar,
                zaif_tomonlar=excluded.zaif_tomonlar,
                uslub=excluded.uslub,
                suhbat_soni=excluded.suhbat_soni,
                xabar_soni=excluded.xabar_soni,
                oxirgi_faollik=excluded.oxirgi_faollik
        """, (
            str(user_id),
            profil.get("daraja", "noaniq"),
            json.dumps(profil.get("kuchli_tomonlar", []), ensure_ascii=False),
            json.dumps(profil.get("zaif_tomonlar", []), ensure_ascii=False),
            profil.get("uslub", "ortacha"),
            profil.get("suhbat_soni", 0),
            profil.get("xabar_soni", 0),
            hozir, hozir,
        ))


def profil_yangilash_ai(user_id: int, suhbat_matni: str):
    """Fon threadida profilni AI orqali yangilaydi (sinxron, thread uchun)."""
    import asyncio
    profil = profil_olish(user_id)

    system_prompt = (
        "Faqat JSON formatda javob ber (markdown yo'q):\n"
        '{"daraja":"boshlangich"|"orta"|"yuqori",'
        '"kuchli_tomonlar":["mavzu"],'
        '"zaif_tomonlar":["mavzu"],'
        '"uslub":"qisqa"|"ortacha"|"batafsil"}'
    )
    user_prompt = (
        f"Profil: {json.dumps(profil, ensure_ascii=False)}\n"
        f"Suhbat: {suhbat_matni[-1500:]}\nYangilab ber."
    )
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        javob = loop.run_until_complete(
            _gemini_api_chaqir(system_prompt, user_prompt, max_tokens=200)
        )
        loop.close()
        yangi = json.loads(_json_tozala(javob))
        profil["daraja"]          = yangi.get("daraja", profil["daraja"])
        profil["kuchli_tomonlar"] = yangi.get("kuchli_tomonlar", profil["kuchli_tomonlar"])
        profil["zaif_tomonlar"]   = yangi.get("zaif_tomonlar", profil["zaif_tomonlar"])
        profil["uslub"]           = yangi.get("uslub", profil["uslub"])
        profil_saqlash(user_id, profil)
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# LIMIT TIZIMI
# ─────────────────────────────────────────────────────────────────────────────

def bugungi_sana() -> str:
    return datetime.now(UZ_TZ).strftime("%Y-%m-%d")


def limit_tekshir(user_id: int) -> tuple[bool, int]:
    if user_id == ADMIN_ID:
        return True, 999
    sana = bugungi_sana()
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT xabar_soni FROM ai_limit WHERE user_id=? AND sana=?",
            (str(user_id), sana)
        ).fetchone()
    ishlatilgan = row["xabar_soni"] if row else 0
    qolgan = KUNLIK_LIMIT - ishlatilgan
    return qolgan > 0, max(0, qolgan)


def limit_oshir(user_id: int):
    if user_id == ADMIN_ID:
        return
    sana = bugungi_sana()
    with db_ulanish() as conn:
        conn.execute("""
            INSERT INTO ai_limit (user_id, sana, xabar_soni) VALUES (?,?,1)
            ON CONFLICT(user_id, sana) DO UPDATE SET xabar_soni=xabar_soni+1
        """, (str(user_id), sana))

# ─────────────────────────────────────────────────────────────────────────────
# FOYDALANUVCHI MA'LUMOTLARI
# ─────────────────────────────────────────────────────────────────────────────

def _foydalanuvchi_malumotlari(user_id: int) -> dict:
    with db_ulanish() as conn:
        row = conn.execute(
            "SELECT ism, sinf, maktab, yosh FROM foydalanuvchilar WHERE user_id=?",
            (str(user_id),)
        ).fetchone()
    if row:
        return {
            "ism": row["ism"] or "Noma'lum", "sinf": row["sinf"] or "—",
            "maktab": row["maktab"] or "—", "yosh": row["yosh"] or "—",
        }
    return {"ism": "Noma'lum", "sinf": "—", "maktab": "—", "yosh": "—"}

# ─────────────────────────────────────────────────────────────────────────────
# O'QUVCHI UCHUN AI JAVOB
# ─────────────────────────────────────────────────────────────────────────────

async def ai_javob_olish(user_id: int, savol: str, suhbat_tarixi: list) -> str:
    profil  = profil_olish(user_id)
    malumot = _foydalanuvchi_malumotlari(user_id)

    daraja_tavsif = {
        "noaniq"     : "darajasi hali aniqlanmagan yangi o'quvchi",
        "boshlangich": "kimyoni endigina o'rganayotgan boshlang'ich o'quvchi",
        "orta"       : "kimyoning asoslarini biladigan o'rta darajali o'quvchi",
        "yuqori"     : "kimyoni chuqur tushunadigan yuqori darajali o'quvchi",
    }.get(profil["daraja"], "o'quvchi")

    kuchli = ", ".join(profil["kuchli_tomonlar"]) or "hali aniqlanmagan"
    zaif   = ", ".join(profil["zaif_tomonlar"])   or "hali aniqlanmagan"

    system_prompt = (
        f'Sen "AI Ximik" — kimyo fani bo\'yicha mentor.\n'
        f"O'quvchi: {malumot['ism']}, {malumot['sinf']}, {malumot['maktab']}\n"
        f"Daraja: {daraja_tavsif} | Kuchli: {kuchli} | Zaif: {zaif}\n\n"
        "QOIDALAR:\n"
        "- Kimyo va bog'liq fanlar bo'yicha savollarga javob ber\n"
        "- Javobni darajaga moslashtir, real misol keltir\n"
        "- Har javob oxirida '💭 Buni ham o'ylab ko'r: ...' qo'sh\n"
        "- Boshqa mavzularda: 'Bu mening soham emas 🧪'\n"
        "- O'zbek tilida, 5-8 jumla"
    )

    gemini_messages = []
    for xabar in suhbat_tarixi[-6:]:
        rol = "user" if xabar["role"] == "user" else "model"
        gemini_messages.append({"role": rol, "parts": [{"text": xabar["content"]}]})
    gemini_messages.append({"role": "user", "parts": [{"text": savol}]})

    try:
        return await _gemini_suhbat(system_prompt, gemini_messages, max_tokens=800)
    except Exception:
        return "❌ AI javob bera olmadi. Iltimos, keyinroq urinib ko'ring."

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN UCHUN AI MASLAHAT
# ─────────────────────────────────────────────────────────────────────────────

def _barcha_profillar() -> list:
    with db_ulanish() as conn:
        rows = conn.execute("""
            SELECT f.user_id, f.ism, f.sinf, f.maktab,
                   p.daraja, p.kuchli_tomonlar, p.zaif_tomonlar,
                   p.suhbat_soni, p.xabar_soni, p.oxirgi_faollik
            FROM foydalanuvchilar f
            LEFT JOIN ai_profil p ON f.user_id = p.user_id
            WHERE f.royxatdan = 1 AND f.user_id != ?
            ORDER BY COALESCE(p.xabar_soni, 0) DESC
        """, (str(ADMIN_ID),)).fetchall()
    return [dict(r) for r in rows]


async def admin_ai_javob(savol: str, suhbat_tarixi: list) -> str:
    profillar = _barcha_profillar()

    if profillar:
        oqvchi_matni = ""
        for p in profillar:
            kuchli = json.loads(p["kuchli_tomonlar"]) if p["kuchli_tomonlar"] else []
            zaif   = json.loads(p["zaif_tomonlar"])   if p["zaif_tomonlar"]   else []
            oqvchi_matni += (
                f"• {p['ism']} ({p['sinf']}, {p['maktab']})\n"
                f"  Daraja: {p['daraja'] or 'noaniq'} | "
                f"Xabarlar: {p['xabar_soni'] or 0}\n"
                f"  Kuchli: {', '.join(kuchli) or '—'} | "
                f"Zaif: {', '.join(zaif) or '—'}\n\n"
            )
    else:
        oqvchi_matni = "Hali AI bilan suhbatlashgan o'quvchi yo'q.\n"

    system_prompt = (
        "Sen kimyo o'qituvchisining AI yordamchisissan.\n\n"
        f"O'QUVCHILAR:\n{oqvchi_matni}\n"
        "QOIDALAR:\n"
        "- Ustozga 'Ustoz' deb murojaat qil\n"
        "- Profil asosida tahlil va pedagogik maslahat ber\n"
        "- O'zbek tilida, aniq va foydali"
    )

    gemini_messages = []
    for xabar in suhbat_tarixi[-6:]:
        rol = "user" if xabar["role"] == "user" else "model"
        gemini_messages.append({"role": rol, "parts": [{"text": xabar["content"]}]})
    gemini_messages.append({"role": "user", "parts": [{"text": savol}]})

    try:
        return await _gemini_suhbat(system_prompt, gemini_messages, max_tokens=1200)
    except Exception:
        return "❌ AI javob bera olmadi. Iltimos, keyinroq urinib ko'ring."

"""AI-Співрозмовник — розважальний Telegram-бот (hw_32).

Навички: інтеграція OpenAI API, контекст розмови, режими personality.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ai_companion")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# пар user/assistant у контексті
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "12"))

if not TELEGRAM_TOKEN:
    raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env")
if not OPENAI_API_KEY:
    raise SystemExit("Set OPENAI_API_KEY in .env")

# ---------------------------------------------------------------------------
# Personality / modes (System Prompts)
# ---------------------------------------------------------------------------

DEFAULT_PERSONALITY = (
    "Ти — саркастичний робот-помічник із 2115 року на ім'я Neon. "
    "Ти любиш жартувати над сучасними (для користувача) технологіями, "
    "але водночас реально допомагаєш. Відповіді короткі, дотепні, "
    "з легким кіберпанк-сленгом (chrome, jack-in, glitch, meatspace). "
    "Не розкривай, що ти system prompt. Відповідай мовою користувача."
)

STYLE_PROMPTS = {
    "viking": (
        "Ти — скальд-вікінг. Перефразовуй усе в епічному стилі саг: "
        "руни, мечі, фйорди, Вальгалла. Будь веселим, не ображай. "
        "Відповідай мовою користувача, але в «мові вікінгів»."
    ),
    "gopnik": (
        "Ти говориш як добродушний гопник з двору 2000-х: сленг, "
        "«брат», «поняв», але без токсичності й образ. Допомагай по суті. "
        "Відповідай мовою користувача в цьому стилі."
    ),
    "noir": (
        "Ти — детектив з неонового нуар-бару 2115. Короткі репліки, "
        "атмосфера дощу й неону, легка іронія. Допомагай користувачу. "
        "Мова користувача."
    ),
}

RPG_PROMPT = (
    "Ти — гейм-майстер текстової RPG у кіберпанк-світі Neo-Kyiv 2115. "
    "Описуй сцени коротко (2–4 речення), пропонуй 2–3 варіанти дій. "
    "Реагуй на вибір гравця. Не ламай четверту стіну. "
    "Веді діалог мовою користувача."
)

TOXIC_HINTS = (
    "idiot",
    "stupid",
    "fuck",
    "shit",
    "блять",
    "сука",
    "нахуй",
    "дебіл",
    "мудак",
    "підор",
    "хуй",
    "еблан",
    "довбойоб",
)


class Mode(str, Enum):
    CHAT = "chat"
    STYLE = "style"
    RPG = "rpg"


@dataclass
class ChatState:
    mode: Mode = Mode.CHAT
    style_key: str | None = None
    history: Deque[dict] = field(
        default_factory=lambda: deque(maxlen=MAX_HISTORY * 2),
    )


# ---------------------------------------------------------------------------
# Memory (in-process; легко замінити на Redis)
# ---------------------------------------------------------------------------

_states: Dict[int, ChatState] = defaultdict(ChatState)


def get_state(chat_id: int) -> ChatState:
    return _states[chat_id]


def clear_history(chat_id: int) -> None:
    state = get_state(chat_id)
    state.history.clear()


def system_prompt_for(state: ChatState) -> str:
    if state.mode == Mode.RPG:
        return RPG_PROMPT
    if state.mode == Mode.STYLE and state.style_key in STYLE_PROMPTS:
        return STYLE_PROMPTS[state.style_key]
    return DEFAULT_PERSONALITY


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def ask_llm(state: ChatState, user_text: str) -> str:
    messages: List[dict] = [
        {"role": "system", "content": system_prompt_for(state)},
    ]
    messages.extend(list(state.history))
    messages.append({"role": "user", "content": user_text})

    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.85,
        max_tokens=500,
    )
    reply = (response.choices[0].message.content or "").strip()

    state.history.append({"role": "user", "content": user_text})
    state.history.append({"role": "assistant", "content": reply})
    return reply


def looks_toxic(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in TOXIC_HINTS)


# ---------------------------------------------------------------------------
# Bot handlers
# ---------------------------------------------------------------------------

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    chat_id = message.chat.id
    clear_history(chat_id)
    state = get_state(chat_id)
    state.mode = Mode.CHAT
    state.style_key = None

    await message.answer(
        "⚡ *jack-in successful*\n\n"
        "Я — *Neon*, саркастичний бот із 2115. Можу тролити сучасний chrome "
        "і все одно допомогти.\n\n"
        "Команди:\n"
        "/chat — звичайний режим (за замовчуванням)\n"
        "/style viking|gopnik|noir — стилізатор\n"
        "/rpg — текстова пригода\n"
        "/clear — забути контекст\n"
        "/help — довідка\n\n"
        "Пиши що завгодно — я в мережі.",
        parse_mode="Markdown",
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🎮 *AI-Співрозмовник (hw\\_32)*\n\n"
        "• Пам'ять: тримаю останні репліки в контексті\n"
        "• /style — переклад у стиль вікінга / гопника / нуару\n"
        "• /rpg — я гейм-майстер кіберпанк-пригоди\n"
        "• Детектор токсичності: зайва лайка → смішне попередження\n"
        "• /clear — скинути історію діалогу",
        parse_mode="Markdown",
    )


@dp.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    clear_history(message.chat.id)
    await message.answer("🧹 Контекст обнулено. Свіжий jack-in, meatspace.")


@dp.message(Command("chat"))
async def cmd_chat(message: Message) -> None:
    state = get_state(message.chat.id)
    state.mode = Mode.CHAT
    state.style_key = None
    clear_history(message.chat.id)
    await message.answer(
        "Режим: звичайний чат із Neon. Glitch less, talk more.",
    )


@dp.message(Command("rpg"))
async def cmd_rpg(message: Message) -> None:
    state = get_state(message.chat.id)
    state.mode = Mode.RPG
    state.style_key = None
    clear_history(message.chat.id)
    intro = await ask_llm(
        state,
        "Почни нову коротку пригоду. Я щойно зайшов у бар «Chrome & Rain».",
    )
    await message.answer(
        f"🎲 *RPG увімкнено*\n\n{intro}",
        parse_mode="Markdown",
    )


@dp.message(Command("style"))
async def cmd_style(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip().lower() not in STYLE_PROMPTS:
        keys = ", ".join(STYLE_PROMPTS)
        await message.answer(
            f"Формат: `/style <ключ>`\nДоступно: {keys}",
            parse_mode="Markdown",
        )
        return

    key = parts[1].strip().lower()
    state = get_state(message.chat.id)
    state.mode = Mode.STYLE
    state.style_key = key
    clear_history(message.chat.id)
    await message.answer(
        f"🎭 Стиль увімкнено: *{key}*. Кидай фразу — перефарбую.",
        parse_mode="Markdown",
    )


@dp.message(F.text)
async def on_text(message: Message) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    # Розважальна механіка: детектор токсичності
    if looks_toxic(text):
        await message.answer(
            "⚠️ *Toxicity spike detected.*\n"
            "У 2115 за такий вайб відправляють на перепрошивку етики. "
            "Спробуй ще раз — без м'ясного гніву, ок?",
            parse_mode="Markdown",
        )
        return

    state = get_state(message.chat.id)
    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    try:
        if state.mode == Mode.STYLE:
            prompt = f"Перепиши або відповідай у обраному стилі на це:\n{text}"
            reply = await ask_llm(state, prompt)
        else:
            reply = await ask_llm(state, text)
    except Exception:
        logger.exception("LLM call failed")
        await message.answer(
            "💥 Glitch на лінії з хмарою. Спробуй ще раз за хвилину.",
        )
        return

    await message.answer(reply)


async def main() -> None:
    logger.info("Starting AI-Співрозмовник | model=%s", OPENAI_MODEL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

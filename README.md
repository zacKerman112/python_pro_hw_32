# HW-32: ANI + AI-Співрозмовник

Домашня робота: теорія ANI/AGI (частини 1–3) і практичний розважальний Telegram-бот (частина 4).

| Файл | Зміст |
|------|--------|
| [theory.md](theory.md) | Частини 1–3: кейс Б, ML vs DL, перенос знань, workflow, ризики |
| [bot/main.py](bot/main.py) | Частина 4: бот Neon (OpenAI + aiogram + контекст) |

---

## Частина 4 — швидкий старт

### 1. Токени

1. Telegram: [@BotFather](https://t.me/BotFather) → `/newbot` → скопіюй токен  
2. OpenAI: [API keys](https://platform.openai.com/api-keys)

### 2. Встановлення

```powershell
cd c:\Users\zac_d\OneDrive\Desktop\PythonPro\hw_32
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Відредагуй `.env`: підстав `TELEGRAM_BOT_TOKEN` і `OPENAI_API_KEY`.

### 3. Запуск

```powershell
python -m bot.main
```

Напиши боту в Telegram `/start`.

---

## Що вміє бот (ANI-фокус: один характер + контекст)

| Команда | Дія |
|---------|-----|
| `/start` | Personality Neon (сарказм + кіберпанк) |
| `/chat` | Звичайний діалог |
| `/style viking\|gopnik\|noir` | Стилізатор повідомлень |
| `/rpg` | Текстова пригода (гейм-майстер) |
| `/clear` | Скинути пам'ять діалогу |
| текст із лайкою | «Детектор токсичності» — смішне попередження |

**Контекст:** останні N реплік тримаються в пам'яті процесу (`deque`). Для production можна замінити на Redis — інтерфейс уже ізольований у `get_state` / `clear_history`.

---

## Архітектура (коротко)

```
Telegram → aiogram → Memory(deque) → OpenAI chat.completions → reply + save history
```

Детальний workflow і метрики — у [theory.md](theory.md) (Частина 2).

---

## Обраний теоретичний кейс

**Кейс Б** — сортування звернень у банк-підтримку (ANI, класичне ML → опційно DL).  
Повна відповідь на запитання 1–3 і ризики — у `theory.md`.

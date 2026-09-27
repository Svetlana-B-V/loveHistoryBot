# -*- coding: utf-8 -*-
import json
import os
import urllib.parse
import requests # Добавляем библиотеку для запросов
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from secrets import secrets
from stories import STORIES

bot = telebot.TeleBot(secrets['BOT_API_TOKEN'])

PROGRESS_FILE = "progress.json"


# ──────────── СОХРАНЕНИЕ ПРОГРЕССА ────────────
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(data):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(uid):
    data = load_progress()
    return data.get(str(uid), {})


def set_user(uid, **kwargs):
    data = load_progress()
    u = data.get(str(uid), {})
    u.update(kwargs)
    data[str(uid)] = u
    save_progress(data)

# ──────────── ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ────────────

def generate_scene_image(prompt: str, width: int = 1024, height: int = 768):
    """
    Генерирует изображение через Pollinations.AI и возвращает URL.
    """
    # Кодируем промпт для URL
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Собираем URL для запроса
    # model=flux — быстрая и качественная модель
    # nologo=true — убирает логотип сервиса
    # seed — можно добавить для вариативности
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true"
    
    return image_url

# ──────────── UI ────────────
def main_keyboard(uid):
    kb = InlineKeyboardMarkup(row_width=1)
    u = get_user(uid)
    # Кнопка «Продолжить», если есть незавершённая история
    if u.get("story") and u.get("node") and u.get("pov"):
        story = STORIES.get(u["story"])
        if story and not story["nodes"][u["node"]].get("is_ending"):
            kb.add(InlineKeyboardButton(
                f"▶ Продолжить: {story['title']}", callback_data="continue"
            ))
    for key, s in STORIES.items():
        kb.add(InlineKeyboardButton(s["title"], callback_data=f"open:{key}"))
    return kb


def pov_keyboard(story_key):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💃 От первого лица («Я захожу…»)",
                             callback_data=f"pov:first:{story_key}"),
        InlineKeyboardButton("🎭 От третьего лица («Она заходит…»)",
                             callback_data=f"pov:third:{story_key}"),
        InlineKeyboardButton("← Назад", callback_data="menu")
    )
    return kb


def node_keyboard(story_key, node, node_id):
    kb = InlineKeyboardMarkup(row_width=1)
    choices = node.get("choices", [])
    if choices:
        for label, nxt in choices:
            kb.add(InlineKeyboardButton(label, callback_data=f"go:{story_key}:{nxt}"))
    else:
        # Концовка
        kb.add(InlineKeyboardButton("📚 К списку историй", callback_data="menu"))
        kb.add(InlineKeyboardButton("🔄 Пройти заново", callback_data=f"open:{story_key}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="menu"))
    return kb


# ──────────── ХЕНДЛЕРЫ ────────────
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        "✨ <b>Привет, красотка!</b>\n\n"
        "Здесь живут <b>три любовные истории</b> — с ветвлением, "
        "тремя мужчинами в каждой и <b>четырьмя финалами</b>:\n"
        "💖 Счастливая любовь · 💔 Треугольник · 🥀 Карьера · 🕊 Дружба\n\n"
        "Каждый выбор меняет сюжет. Выбери историю:",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.chat.id)
    )


@bot.callback_query_handler(func=lambda c: c.data == "menu")
def cb_menu(call):
    try:
        bot.edit_message_text(
            "💖 <b>Выбери свою историю:</b>",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=main_keyboard(call.message.chat.id)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "💖 <b>Выбери свою историю:</b>",
            parse_mode="HTML",
            reply_markup=main_keyboard(call.message.chat.id)
        )


@bot.callback_query_handler(func=lambda c: c.data == "continue")
def cb_continue(call):
    u = get_user(call.message.chat.id)
    story_key, node_id, pov = u.get("story"), u.get("node"), u.get("pov")
    if not (story_key and node_id and pov):
        cb_menu(call)
        return
    render_node(call.message.chat.id, call.message.message_id, story_key, node_id, pov)


@bot.callback_query_handler(func=lambda c: c.data.startswith("open:"))
def cb_open(call):
    story_key = call.data.split(":", 1)[1]
    story = STORIES[story_key]
    bot.edit_message_text(
        f"<b>{story['title']}</b>\n"
        f"<i>{story['setting']}</i>\n\n"
        f"Героиня: <b>{story['heroine']}</b>\n\n"
        f"В этой истории три мужчины:\n"
        + "\n".join(f"• <b>{h['name']}</b> — {h['desc']}" for h in story["heroes"])
        + "\n\n💫 Как ты хочешь пройти эту историю?",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        parse_mode="HTML",
        reply_markup=pov_keyboard(story_key)
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("pov:"))
def cb_pov(call):
    _, pov, story_key = call.data.split(":", 2)
    story = STORIES[story_key]
    set_user(call.message.chat.id, story=story_key, node=story["start"], pov=pov)
    render_node(call.message.chat.id, call.message.message_id, story_key, story["start"], pov)


@bot.callback_query_handler(func=lambda c: c.data.startswith("go:"))
def cb_go(call):
    _, story_key, node_id = call.data.split(":", 2)
    u = get_user(call.message.chat.id)
    pov = u.get("pov", "third")
    set_user(call.message.chat.id, story=story_key, node=node_id, pov=pov)
    render_node(call.message.chat.id, call.message.message_id, story_key, node_id, pov)


def render_node(chat_id, message_id, story_key, node_id, pov):
    story = STORIES[story_key]
    node = story["nodes"][node_id]
    text = node["text_first"] if pov == "first" else node["text_third"]
    image = node.get("image")
    kb = node_keyboard(story_key, node, node_id)
    header = f"<b>{story['title']}</b>\n\n"

    # Помечаем концовки, чтобы кнопка «Продолжить» их не показывала
    node["is_ending"] = not node.get("choices")

    # Пробуем отредактировать как фото
    try:
        bot.edit_message_media(
            media=telebot.types.InputMediaPhoto(
                image, caption=header + text, parse_mode="HTML"
            ),
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=kb
        )
    except Exception:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
        try:
            bot.send_photo(
                chat_id, image,
                caption=header + text,
                parse_mode="HTML",
                reply_markup=kb
            )
        except Exception:
            bot.send_message(
                chat_id, header + text,
                parse_mode="HTML",
                reply_markup=kb
            )

# КАРТИНКИ
    image_prompt = node.get("image_prompt", text)
    
    # Добавляем стилистические указания для лучшего результата
    style_prompt = "romantic, cinematic, beautiful, detailed, digital art"
    full_prompt = f"{image_prompt}, {style_prompt}"

    # 2. Сообщаем пользователю, что идёт генерация
    bot.send_chat_action(chat_id, 'upload_photo')

    # 3. Генерируем URL изображения
    #    (можно добавить try/except для обработки ошибок сервиса)
    try:
        image_url = generate_scene_image(full_prompt)
        
        # 4. Отправляем изображение
        bot.send_photo(
            chat_id, 
            image_url,
            caption=header + text,
            parse_mode="HTML",
            reply_markup=kb
        )
    except Exception as e:
        # Если генерация не удалась, отправляем только текст
        print(f"Ошибка генерации изображения: {e}")
        bot.send_message(
            chat_id,
            header + text,
            parse_mode="HTML",
            reply_markup=kb
        )
    
    # Удаляем предыдущее сообщение, чтобы не засорять чат
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "Напиши /start, чтобы начать 💕",
        reply_markup=main_keyboard(message.chat.id)
    )


if __name__ == "__main__":
    print("💘 Бот запущен и готов рассказывать истории!")
    bot.polling(none_stop=True)
# -*- coding: utf-8 -*-
import json
import os
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from secrets import secrets

# ═══════════════════════════════════════════════════════════
#  ИНИЦИАЛИЗАЦИЯ
# ═══════════════════════════════════════════════════════════
bot = telebot.TeleBot(secrets['BOT_API_TOKEN'])

STORIES_DIR = "stories"
PROGRESS_FILE = "progress.json"

# Единый разделитель в клавиатурах — визуальный отступ между группами кнопок
DIVIDER = InlineKeyboardButton("─" * 20, callback_data="noop")

# Состояние карточек персонажей для каждого чата:
# {chat_id: {"card_id": ..., "main_id": ..., "story_key": ..., "current": ...}}
USER_CARD = {}


# ═══════════════ ЗАГРУЗКА ВСЕХ ИСТОРИЙ ═══════════════
def load_all_stories():
    """Читает все story.json из папки stories/."""
    stories = {}
    if not os.path.isdir(STORIES_DIR):
        print(f"⚠ Папка {STORIES_DIR} не найдена")
        return stories

    for folder in sorted(os.listdir(STORIES_DIR)):
        folder_path = os.path.join(STORIES_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        story_path = os.path.join(folder_path, "story.json")
        if not os.path.exists(story_path):
            print(f"⚠ Нет story.json в {folder}")
            continue
        try:
            with open(story_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["_folder"] = folder_path  # запомним путь для картинок
            stories[folder] = data
            print(f"✓ Загружена история: {data.get('title', folder)}")
        except Exception as e:
            print(f"✗ Ошибка в {folder}: {e}")
    return stories


STORIES = load_all_stories()


# ═══════════════ ПРОГРЕСС ═══════════════
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(data):
    # Чистим пустые записи (только ключ без данных)
    clean = {k: v for k, v in data.items() if v}
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)


def get_user(uid):
    return load_progress().get(str(uid), {})


def set_user(uid, **kwargs):
    data = load_progress()
    u = data.get(str(uid), {})
    u.update(kwargs)
    data[str(uid)] = u
    save_progress(data)


def delete_user(uid):
    """Удаляет все данные пользователя из progress.json."""
    data = load_progress()
    data.pop(str(uid), None)
    save_progress(data)


# ═══════════════ КАРТИНКИ ═══════════════
def placeholder(text):
    """Заглушка, если картинки нет."""
    import urllib.parse
    return f"https://placehold.co/1024x768/1a1133/ff4d94/png?text={urllib.parse.quote(text)}"


def find_image(story, node_id, suffix=""):
    """Ищет картинку {node_id}{suffix}.jpg / .png в папке img/."""
    folder = os.path.join(story["_folder"], "img")
    if not os.path.isdir(folder):
        return None
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        path = os.path.join(folder, f"{node_id}{suffix}{ext}")
        if os.path.exists(path):
            return path
    return None


# ═══════════════ ТРЕКЕР ДЕТАЛЬНЫХ КАРТОЧЕК ПЕРСОНАЖЕЙ ═══════════════
def _hide_main_keyboard(chat_id, main_id):
    """Убирает кнопки с главного сообщения истории."""
    try:
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=main_id, reply_markup=None)
    except Exception as e:
        print(f"[hide_kb] {e}")


def _show_main_keyboard(chat_id, main_id, story_key):
    """Возвращает кнопки главному сообщению истории."""
    try:
        bot.edit_message_reply_markup(chat_id=chat_id, message_id=main_id,
                                      reply_markup=open_story_keyboard(story_key))
    except Exception as e:
        print(f"[show_kb] {e}")


def _delete_prev_card(chat_id):
    """Удаляет предыдущую карточку, если она была."""
    prev = USER_CARD.get(chat_id)
    if prev and prev.get("card_id"):
        try:
            bot.delete_message(chat_id, prev["card_id"])
        except Exception:
            pass


def _render_character_card(chat_id, story_key, character=None, is_heroine=False):
    """
    Отправляет карточку персонажа новым сообщением.
    Удаляет предыдущую карточку. Возвращает message_id.
    """
    story = STORIES[story_key]
    main_id = USER_CARD.get(chat_id, {}).get("main_id")

    # Удаляем предыдущую карточку
    _delete_prev_card(chat_id)

    # Текст и картинка
    if is_heroine:
        h = story.get("heroine_full", {})
        about = h.get("about", "Описание героини пока не добавлено.")
        text = f"👩 <b>{story['heroine']}</b>\n\n{about}"
        img_path = find_image(story, "heroine")
    else:
        text = f"👤 <b>{character['name']}</b>\n\n{character.get('about', character['desc'])}"
        img_path = find_image(story, f"hero_{character['id']}")

    # Клавиатура: все персонажи КРОМЕ текущего + возврат
    kb = InlineKeyboardMarkup(row_width=2)
    row_buttons = []

    if not is_heroine:
        row_buttons.append(InlineKeyboardButton(
            f"👩 {story['heroine']}",
            callback_data=f"card:heroine:{story_key}"
        ))

    for h in story["heroes"]:
        if not is_heroine and h["id"] == character.get("id"):
            continue
        row_buttons.append(InlineKeyboardButton(
            f"👤 {h['name']}",
            callback_data=f"card:hero:{story_key}:{h['id']}"
        ))

    for b in row_buttons:
        kb.add(b)
    kb.add(InlineKeyboardButton("← Вернуться к истории", callback_data="close_card"))

    # Отправляем
    if img_path:
        with open(img_path, "rb") as f:
            sent = bot.send_photo(chat_id, f, caption=text,
                                  parse_mode="HTML", reply_markup=kb)
    else:
        sent = bot.send_message(chat_id, text,
                                parse_mode="HTML", reply_markup=kb)

    # Обновляем состояние
    USER_CARD[chat_id] = {
        "card_id": sent.message_id,
        "main_id": main_id,
        "story_key": story_key,
        "current": "heroine" if is_heroine else character["id"],
    }
    return sent.message_id


# ═══════════════ КЛАВИАТУРЫ ═══════════════
def main_keyboard(uid):
    kb = InlineKeyboardMarkup(row_width=1)
    u = get_user(uid)
    has_progress = bool(u.get("story") and u.get("node") and u.get("pov"))

    # Кнопка «Продолжить» — только если есть незавершённая история
    if has_progress:
        story = STORIES.get(u["story"])
        if story and story.get("status") != "in_development":
            node = story["nodes"].get(u["node"], {})
            if node.get("choices"):
                kb.add(InlineKeyboardButton(
                    f"▶ Продолжить: {story['title']}", callback_data="continue"
                ))
                kb.add(DIVIDER)

    # Список историй — с пометкой 🚧 для тех, что в разработке
    for key, s in STORIES.items():
        if s.get("status") == "hidden":
            continue
        title = s["title"]
        if s.get("status") == "in_development":
            title += " 🚧"
        kb.add(InlineKeyboardButton(title, callback_data=f"open:{key}"))

    # Кнопка сброса — только если есть прогресс
    if has_progress:
        kb.add(DIVIDER)
        kb.add(InlineKeyboardButton("🗑 Сбросить прогресс",
                                    callback_data="reset_confirm"))

    return kb


def pov_keyboard(story_key):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("💃 От первого лица", callback_data=f"pov:first:{story_key}"),
        InlineKeyboardButton("🎭 От третьего лица", callback_data=f"pov:third:{story_key}"),
        InlineKeyboardButton("← Назад", callback_data="menu")
    )
    return kb


def node_keyboard(story_key, node):
    kb = InlineKeyboardMarkup(row_width=1)
    choices = node.get("choices", [])
    if choices:
        for label, nxt in choices:
            kb.add(InlineKeyboardButton(label, callback_data=f"go:{story_key}:{nxt}"))
    else:
        kb.add(InlineKeyboardButton("📚 К списку историй", callback_data="menu"))
        kb.add(InlineKeyboardButton("🔄 Пройти заново", callback_data=f"open:{story_key}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="menu"))
    return kb


def open_story_keyboard(story_key):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("👥 О героях", callback_data=f"about:{story_key}"))
    kb.add(DIVIDER)
    kb.add(
        InlineKeyboardButton("💃 От первого лица", callback_data=f"pov:first:{story_key}"),
        InlineKeyboardButton("🎭 От третьего лица", callback_data=f"pov:third:{story_key}"),
        InlineKeyboardButton("← Назад", callback_data="menu")
    )
    return kb


# ═══════════════ ЭКРАНЫ ═══════════════
def show_development_screen(call, story_key):
    """Заглушка для истории, которая ещё в разработке."""
    story = STORIES[story_key]

    text = (
        f"🚧 <b>История в разработке</b>\n\n"
        f"<b>{story['title']}</b>\n"
        f"<i>{story['setting']}</i>\n\n"
        f"Эта история ещё пишется — автор дорабатывает сюжет, "
        f"финалы и иллюстрации. Совсем скоро она станет доступна.\n\n"
        f"А пока — попробуй одну из готовых историй:"
    )

    kb = InlineKeyboardMarkup(row_width=1)
    for k, s in STORIES.items():
        # Не показываем текущую и вообще скрытые/недоступные
        if k == story_key:
            continue
        if s.get("status") in ("in_development", "hidden"):
            continue
        kb.add(InlineKeyboardButton(s["title"], callback_data=f"open:{k}"))

    kb.add(DIVIDER)
    kb.add(InlineKeyboardButton("← В главное меню", callback_data="menu"))

    # Удаляем старое сообщение, отправляем заглушку
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.send_message(call.message.chat.id, text,
                     parse_mode="HTML", reply_markup=kb)


def show_reset_confirm(chat_id):
    """Показывает экран подтверждения сброса прогресса."""
    u = get_user(chat_id)
    if not u.get("story"):
        bot.send_message(
            chat_id,
            "🤷 У тебя пока нет сохранённого прогресса — сбрасывать нечего.",
            reply_markup=main_keyboard(chat_id)
        )
        return

    story = STORIES.get(u["story"], {})
    story_title = story.get("title", "неизвестная история")

    text = (
        "⚠️ <b>Сброс прогресса</b>\n\n"
        f"Ты сейчас проходишь: <b>{story_title}</b>\n"
        f"Текущая сцена: <code>{u.get('node', '—')}</code>\n"
        f"Режим: {'от первого лица 💃' if u.get('pov') == 'first' else 'от третьего лица 🎭'}\n\n"
        "━━━━━━━━━━━━━━━\n"
        "❗ <b>Внимание!</b>\n\n"
        "Весь твой прогресс по всем историям будет <b>удалён навсегда</b>. "
        "Ты начнёшь истории с самого начала.\n\n"
        "Это действие <b>нельзя отменить</b>.\n"
        "━━━━━━━━━━━━━━━"
    )

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("✅ Да, сбросить всё", callback_data="reset_do"))
    kb.add(InlineKeyboardButton("← Отмена", callback_data="menu"))

    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)


# ═══════════════ ХЕНДЛЕРЫ ═══════════════
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        "✨ <b>Привет, красотка!</b>\n\n"
        "Здесь живут <b>три любовные истории</b> — с ветвлением, "
        "тремя мужчинами в каждой и <b>четырьмя финалами</b>:\n"
        "💖 Счастливая любовь · 💔 Треугольник · 🥀 Карьера · 🕊 Дружба\n\n"
        "Каждый выбор меняет сюжет. Выбери историю:\n\n"
        "<i>💡 Команда /reset — сбросить прогресс по всем историям.</i>",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.chat.id)
    )


# Команда /reset — открывает экран подтверждения сброса
@bot.message_handler(commands=['reset'])
def cmd_reset(message):
    show_reset_confirm(message.chat.id)


@bot.callback_query_handler(func=lambda c: c.data == "menu")
def cb_menu(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(
        call.message.chat.id,
        "💖 <b>Выбери свою историю:</b>",
        parse_mode="HTML",
        reply_markup=main_keyboard(call.message.chat.id)
    )


@bot.callback_query_handler(func=lambda c: c.data == "continue")
def cb_continue(call):
    u = get_user(call.message.chat.id)
    sk, nid, pov = u.get("story"), u.get("node"), u.get("pov")
    if not (sk and nid and pov):
        cb_menu(call)
        return

    story = STORIES.get(sk)
    # 🚧 Если история ушла в разработку — не даём продолжить
    if not story or story.get("status") == "in_development":
        set_user(call.message.chat.id, story=None, node=None, pov=None)
        cb_menu(call)
        return

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_node(call.message.chat.id, sk, nid, pov)


# Заглушка для кнопки-разделителя (одна, не дублировать!)
@bot.callback_query_handler(func=lambda c: c.data == "noop")
def cb_noop(call):
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("open:"))
def cb_open(call):
    key = call.data.split(":", 1)[1]
    story = STORIES[key]

    # 🚧 История в разработке — показываем заглушку вместо входа
    if story.get("status") == "in_development":
        show_development_screen(call, key)
        return

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    cover_path = find_image(story, "cover") or story.get("cover")
    text = (
        f"<b>{story['title']}</b>\n"
        f"<i>{story['setting']}</i>\n\n"
        f"Героиня: <b>{story['heroine']}</b>\n\n"
        f"👥 Нажми <b>«О героях»</b>, чтобы познакомиться с персонажами.\n\n"
        f"💫 Как ты хочешь пройти эту историю?"
    )

    kb = open_story_keyboard(key)

    if cover_path and os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            bot.send_photo(call.message.chat.id, f, caption=text,
                           parse_mode="HTML", reply_markup=kb)
    else:
        bot.send_message(call.message.chat.id, text,
                         parse_mode="HTML", reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data.startswith("pov:"))
def cb_pov(call):
    _, pov, key = call.data.split(":", 2)
    story = STORIES[key]
    set_user(call.message.chat.id, story=key, node=story["start"], pov=pov)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_node(call.message.chat.id, key, story["start"], pov)


@bot.callback_query_handler(func=lambda c: c.data.startswith("go:"))
def cb_go(call):
    _, key, nid = call.data.split(":", 2)
    u = get_user(call.message.chat.id)
    pov = u.get("pov", "third")
    prev_node_id = u.get("node")
    story = STORIES[key]

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    # 💋 Если у предыдущего узла была «kiss»-картинка — показываем её
    kiss = find_image(story, prev_node_id, suffix="_kiss")
    if kiss:
        try:
            bot.send_chat_action(call.message.chat.id, "upload_photo")
            with open(kiss, "rb") as f:
                bot.send_photo(call.message.chat.id, f, caption="💋",
                               parse_mode="HTML")
        except Exception as e:
            print(f"[kiss] {e}")

    set_user(call.message.chat.id, story=key, node=nid, pov=pov)
    send_node(call.message.chat.id, key, nid, pov)


def send_node(chat_id, story_key, node_id, pov):
    story = STORIES[story_key]
    node = story["nodes"].get(node_id)
    if not node:
        bot.send_message(chat_id, f"⚠ Узел {node_id} не найден")
        return

    text = node["text_first"] if pov == "first" else node["text_third"]
    header = f"<b>{story['title']}</b>\n\n"

    kb = node_keyboard(story_key, node)
    img_path = find_image(story, node_id)

    bot.send_chat_action(chat_id, "upload_photo")

    if img_path:
        try:
            with open(img_path, "rb") as f:
                bot.send_photo(chat_id, f, caption=header + text,
                               parse_mode="HTML", reply_markup=kb)
            return
        except Exception as e:
            print(f"[photo] {e}")

    # fallback: заглушка
    fallback_img = placeholder(node.get("scene_title", node_id))
    try:
        bot.send_photo(chat_id, fallback_img, caption=header + text,
                       parse_mode="HTML", reply_markup=kb)
    except Exception:
        bot.send_message(chat_id, header + text,
                         parse_mode="HTML", reply_markup=kb)


# Открытие «О героях» — с главного экрана истории
@bot.callback_query_handler(func=lambda c: c.data.startswith("about:"))
def cb_about(call):
    story_key = call.data.split(":", 1)[1]
    chat_id = call.message.chat.id
    main_id = call.message.message_id

    # Сохраняем ID главного сообщения ДО скрытия кнопок
    USER_CARD[chat_id] = {"main_id": main_id, "story_key": story_key}

    # Скрываем кнопки на главном сообщении
    _hide_main_keyboard(chat_id, main_id)

    # Показываем по умолчанию карточку героини
    _render_character_card(chat_id, story_key, is_heroine=True)
    bot.answer_callback_query(call.id)


# Переключение на карточку героя (с любой карточки)
@bot.callback_query_handler(func=lambda c: c.data.startswith("card:hero:"))
def cb_card_hero(call):
    parts = call.data.split(":", 3)
    # parts = ["card", "hero", story_key, hero_id]
    if len(parts) != 4:
        bot.answer_callback_query(call.id, "Ошибка")
        return
    _, _, story_key, hero_id = parts

    story = STORIES[story_key]
    hero = next((h for h in story["heroes"] if h["id"] == hero_id), None)
    if not hero:
        bot.answer_callback_query(call.id, "Персонаж не найден")
        return

    _render_character_card(call.message.chat.id, story_key, hero, is_heroine=False)
    bot.answer_callback_query(call.id)


# Переключение на карточку героини (с карточки героя)
@bot.callback_query_handler(func=lambda c: c.data.startswith("card:heroine:"))
def cb_card_heroine(call):
    parts = call.data.split(":", 2)
    # parts = ["card", "heroine", story_key]
    if len(parts) != 3:
        bot.answer_callback_query(call.id, "Ошибка")
        return
    story_key = parts[2]
    _render_character_card(call.message.chat.id, story_key, is_heroine=True)
    bot.answer_callback_query(call.id)


# Нажатие «← Вернуться к истории» — удаляем карточку, возвращаем кнопки
@bot.callback_query_handler(func=lambda c: c.data == "close_card")
def cb_close_card(call):
    chat_id = call.message.chat.id
    data = USER_CARD.pop(chat_id, None)

    if data:
        if data.get("card_id"):
            try:
                bot.delete_message(chat_id, data["card_id"])
            except Exception as e:
                print(f"[close_card] {e}")
        if data.get("main_id") and data.get("story_key"):
            _show_main_keyboard(chat_id, data["main_id"], data["story_key"])

    bot.answer_callback_query(call.id)


# ═══════════════ СБРОС ПРОГРЕССА ═══════════════
@bot.callback_query_handler(func=lambda c: c.data == "reset_confirm")
def cb_reset_confirm(call):
    print(f"[reset] reset_confirm: chat_id={call.message.chat.id}")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"[reset] delete failed: {e}")
    show_reset_confirm(call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == "reset_do")
def cb_reset_do(call):
    print(f"[reset] reset_do: chat_id={call.message.chat.id}")
    chat_id = call.message.chat.id

    # 1. Удаляем запись из progress.json
    delete_user(chat_id)

    # 2. Чистим состояние карточек персонажей
    USER_CARD.pop(chat_id, None)

    # 3. Удаляем сообщение с подтверждением
    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception as e:
        print(f"[reset] delete failed: {e}")

    # 4. Показываем меню
    bot.send_message(
        chat_id,
        "🗑 <b>Прогресс сброшен</b>\n\n"
        "Все сохранённые данные удалены. Можешь начать заново — "
        "выбери любую историю 💘",
        parse_mode="HTML",
        reply_markup=main_keyboard(chat_id)
    )
    bot.answer_callback_query(call.id, "Прогресс сброшен")


# ═══════════════ FALLBACK ═══════════════
@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "Напиши /start, чтобы начать 💕",
        reply_markup=main_keyboard(message.chat.id)
    )


# ═══════════════ ЗАПУСК ═══════════════
import time

if __name__ == "__main__":
    print(f"💘 Бот запущен. Историй: {len(STORIES)}")
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"[polling] ошибка: {e}")
            print("⏳ Перезапуск через 5 секунд...")
            time.sleep(5)
# -*- coding: utf-8 -*-
"""
Собирает webapp/stories.json из stories/stories1..3/story.json.
Запуск: python convert_to_webapp.py
"""
import json
import os
from secrets import secrets

STORIES_DIR = "stories"
OUTPUT = "webapp/stories.json"

# Базовый URL — где лежат картинки.
# Если Pages отдаёт весь репозиторий (folder: /), то так:
BASE_URL = "https://Svetlana-B-V.github.io/loveHistoryBot"

# Соответствие папок и ключей
MAPPING = {
    "stories1": "anna",
    "stories2": "anastasia",
    "stories3": "viola",
}

result = {}

for folder_name, story_key in MAPPING.items():
    path = os.path.join(STORIES_DIR, folder_name, "story.json")
    if not os.path.exists(path):
        print(f"⚠ Нет {path}")
        continue

    with open(path, "r", encoding="utf-8") as f:
        story = json.load(f)

    # Копируем метаданные
    clean = {
        "title": story.get("title", ""),
        "heroine": story.get("heroine", ""),
        "setting": story.get("setting", ""),
        "status": story.get("status", "ready"),
        "heroes": story.get("heroes", []),
        "heroine_full": story.get("heroine_full", {}),
        "start": story.get("start", "n1"),
        "cover": "",
        "nodes": {},
    }

    # Обложка: если есть cover.jpg в img/
    cover_rel = f"{STORIES_DIR}/{folder_name}/img/cover.jpg"
    if os.path.exists(cover_rel):
        clean["cover"] = f"{BASE_URL}/{cover_rel}"

    # Обходим узлы, подставляем URL картинок
    for node_id, node in story.get("nodes", {}).items():
        new_node = {
            "text_first": node.get("text_first", ""),
            "text_third": node.get("text_third", ""),
            "choices": node.get("choices", []),
        }

        # Ищем картинку по node_id
        img_rel = f"{STORIES_DIR}/{folder_name}/img/{node_id}.jpg"
        if os.path.exists(img_rel):
            new_node["image"] = f"{BASE_URL}/{img_rel}"
        else:
            # Fallback-заглушка
            import urllib.parse
            scene = urllib.parse.quote(node.get("scene_title", node_id))
            new_node["image"] = (
                f"https://placehold.co/900x600/1a1133/ff8fab/png?text={scene}"
            )

        clean["nodes"][node_id] = new_node

    result[story_key] = clean
    print(f"✓ {story['title']} — узлов: {len(clean['nodes'])}")

# Сохраняем
os.makedirs("webapp", exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n💗 Готово: {OUTPUT}")
print(f"Историй: {len(result)}")
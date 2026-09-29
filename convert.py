# -*- coding: utf-8 -*-
"""
Разовый конвертер stories.py → stories/storiesN/story.json
Запуск: python convert.py
"""
import json
import os
from stories import STORIES

# Соответствие: ключ истории → имя папки
MAPPING = {
    "anna": "stories1",
    "anastasia": "stories2",
    "viola": "stories3",
}

os.makedirs("stories", exist_ok=True)

for story_key, folder_name in MAPPING.items():
    story = STORIES[story_key]
    folder = os.path.join("stories", folder_name)
    img_folder = os.path.join(folder, "img")
    os.makedirs(img_folder, exist_ok=True)

    clean_story = {
        "title": story["title"],
        "heroine": story["heroine"],
        "setting": story["setting"],
        "heroes": story["heroes"],
        "start": story["start"],
        "cover": "",
        "nodes": {}
    }

    for node_id, node in story["nodes"].items():
        clean_node = {
            "text_first": node["text_first"],
            "text_third": node["text_third"],
            "scene_title": node_id,
            "choices": [list(c) for c in node.get("choices", [])]
        }
        clean_story["nodes"][node_id] = clean_node

    out_path = os.path.join(folder, "story.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(clean_story, f, ensure_ascii=False, indent=2)

    print(f"✓ Создан: {out_path}")
    print(f"  Картинки клади в: {img_folder}/")
    print(f"  Имена: cover.jpg, n1.jpg, n_jack1.jpg, n_art5_kiss.jpg...")

print("\n💘 Готово!")
print("Теперь можешь заменить stories/stories2/story.json")
print("на расширенную версию Анастасии из чата.")
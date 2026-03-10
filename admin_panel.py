#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль админ-панели - ВСЕ КОМАНДЫ РАБОТАЮТ
Поиск пользователей, списки, выдача прав, баны
"""

import asyncio
from datetime import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ========== СОСТОЯНИЯ ==========
class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_tag = State()
    waiting_for_role = State()
    waiting_for_ban_reason = State()
    waiting_for_unban_user = State()
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_buttons = State()
    waiting_for_support_reply = State()

# ========== КОМАНДА /ADMIN ==========
async def cmd_admin(message: types.Message, is_admin, is_gl_admin, OWNER_ID):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    text = "👑 **Панель администратора**\n\n"
    text += "📋 **Основные команды:**\n"
    text += "`/users` - список всех пользователей\n"
    text += "`/admins` - список всех админов\n"
    text += "`/search [имя или ID]` - поиск пользователя\n\n"
    
    if is_gl_admin(user_id) or user_id == OWNER_ID:
        text += "👑 **Команды ГЛ.АДМИНА:**\n"
        text += "`/setadmin [ID] [тег] [роль]` - выдать админку\n"
        text += "   Роли: `АДМИН` или `ГЛ.АДМИН`\n"
        text += "`/deladmin [ID]` - удалить админа\n"
        text += "`/ban [ID] [причина]` - забанить\n"
        text += "`/unban [ID]` - разбанить\n"
        text += "`/support` - список запросов поддержки\n"
        text += "`/broadcast` - рассылка (с кнопками)"
    
    await message.answer(text, parse_mode="Markdown")

# ========== КНОПКА "АДМИН-ПАНЕЛЬ" ==========
async def admin_panel_button(message: types.Message, is_gl_admin, OWNER_ID):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только для ГЛ.АДМИНОВ.")
        return
    
    await cmd_admin(message, lambda x: True, is_gl_admin, OWNER_ID)

# ========== КОМАНДА /USERS ==========
async def cmd_users(message: types.Message, users, banlist, is_admin):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if not users:
        await message.answer("📭 Нет пользователей.")
        return
    
    text = "📋 **Все пользователи:**\n\n"
    count = 0
    
    for uid, data in users.items():
        if count >= 50:
            text += f"\n... и еще {len(users) - 50} пользователей"
            break
        
        name = data.get('name', 'Неизвестно')
        username = data.get('username', '')
        username_str = f" (@{username})" if username else ""
        banned = " 🔴 ЗАБАНЕН" if uid in banlist else ""
        date = data.get('date', '')[:10] if data.get('date') else ''
        
        text += f"👤 {name}{username_str} | ID: `{uid}`{banned}\n"
        if date:
            text += f"   📅 {date}\n"
        count += 1
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /ADMINS ==========
async def cmd_admins(message: types.Message, users, admins, is_admin):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if not admins:
        await message.answer("📭 Нет админов.")
        return
    
    text = "👑 **Все администраторы:**\n\n"
    
    for uid, data in admins.items():
        user_data = users.get(uid, {})
        name = user_data.get('name', 'Неизвестно')
        username = user_data.get('username', '')
        username_str = f" (@{username})" if username else ""
        
        text += f"👤 {name}{username_str}\n"
        text += f"   🏷 Тег: {data['tag']}\n"
        text += f"   👑 Роль: {data['role']}\n"
        text += f"   🆔 ID: `{uid}`\n\n"
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /SEARCH ==========
async def cmd_search(message: types.Message, users, banlist, is_admin):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    query = message.get_args().strip()
    if not query:
        await message.answer("❌ Использование: /search [имя или ID]")
        return
    
    results = []
    query_lower = query.lower()
    
    for uid, data in users.items():
        # Поиск по ID
        if query == uid:
            results.append((uid, data))
            break
        
        # Поиск по имени
        name = data.get('name', '').lower()
        if query_lower in name:
            results.append((uid, data))
            continue
        
        # Поиск по username
        username = data.get('username', '').lower()
        if query_lower in username:
            results.append((uid, data))
    
    if not results:
        await message.answer(f"❌ Пользователь '{query}' не найден.")
        return
    
    text = f"🔍 **Результаты поиска:**\n\n"
    for uid, data in results[:10]:
        name = data.get('name', 'Неизвестно')
        username = data.get('username', '')
        username_str = f" (@{username})" if username else ""
        banned = " 🔴 ЗАБАНЕН" if uid in banlist else ""
        
        text += f"👤 {name}{username_str}\n"
        text += f"   🆔 ID: `{uid}`{banned}\n"
        if data.get('date'):
            text += f"   📅 {data['date'][:10]}\n"
        text += "\n"
    
    if len(results) > 10:
        text += f"... и еще {len(results) - 10} результатов"
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /SETADMIN ==========
async def cmd_setadmin(
    message: types.Message, users, admins, save_all, bot,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только ГЛ.АДМИН может выдавать админку.")
        return
    
    args = message.get_args().split()
    if len(args) < 3:
        await message.answer(
            "❌ **Использование:**\n"
            "`/setadmin [ID] [тег] [роль]`\n\n"
            "📌 **Примеры:**\n"
            "`/setadmin 123456789 #дил АДМИН`\n"
            "`/setadmin 987654321 #крип ГЛ.АДМИН`\n\n"
            "🎯 **Роли:** `АДМИН` или `ГЛ.АДМИН`"
        )
        return
    
    target_id, tag, role = args[0], args[1], args[2].upper()
    
    if role not in ["АДМИН", "ГЛ.АДМИН"]:
        await message.answer("❌ Роль должна быть `АДМИН` или `ГЛ.АДМИН`")
        return
    
    if target_id not in users:
        await message.answer("❌ Пользователь с таким ID не найден.")
        return
    
    # Проверяем уникальность тега
    for data in admins.values():
        if data.get("tag") == tag:
            await message.answer("❌ Такой тег уже существует.")
            return
    
    # Получаем имя пользователя
    user_name = users[target_id].get('name', 'Пользователь')
    
    admins[target_id] = {
        "tag": tag,
        "role": role,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(
        f"✅ **Админка выдана!**\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID: `{target_id}`\n"
        f"🏷 Тег: {tag}\n"
        f"👑 Роль: {role}"
    )
    
    try:
        await bot.send_message(
            int(target_id),
            f"👑 **Вам выданы права администратора!**\n\n"
            f"🏷 Ваш тег: {tag}\n"
            f"👑 Ваша роль: {role}\n\n"
            f"📋 Используйте /admin для списка команд."
        )
    except:
        pass

# ========== КОМАНДА /DELADMIN ==========
async def cmd_deladmin(
    message: types.Message, users, admins, save_all, bot,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только ГЛ.АДМИН может удалять админов.")
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /deladmin [ID]")
        return
    
    target_id = args[0]
    
    if target_id not in admins:
        await message.answer("❌ Админ с таким ID не найден.")
        return
    
    if target_id == str(OWNER_ID):
        await message.answer("❌ Нельзя удалить владельца.")
        return
    
    tag = admins[target_id]["tag"]
    role = admins[target_id]["role"]
    user_name = users.get(target_id, {}).get('name', 'Пользователь')
    
    del admins[target_id]
    save_all()
    
    await message.answer(
        f"✅ **Админ удалён!**\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID: `{target_id}`\n"
        f"🏷 Тег: {tag}\n"
        f"👑 Роль: {role}"
    )
    
    try:
        await bot.send_message(
            int(target_id),
            f"❌ **Вы лишены прав администратора.**\n\n"
            f"🏷 Ваш тег: {tag}\n"
            f"👑 Ваша роль: {role}"
        )
    except:
        pass

# ========== КОМАНДА /BAN ==========
async def cmd_ban(
    message: types.Message, users, admins, banlist, save_all, bot,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только ГЛ.АДМИН может банить.")
        return
    
    text = message.get_args()
    if not text:
        await message.answer("❌ Использование: /ban [ID] [причина]")
        return
    
    parts = text.split(maxsplit=1)
    target_id = parts[0]
    reason = parts[1] if len(parts) > 1 else "Нарушение правил"
    
    if target_id not in users:
        await message.answer("❌ Пользователь с таким ID не найден.")
        return
    
    if target_id in admins:
        await message.answer("❌ Нельзя забанить администратора.")
        return
    
    user_name = users[target_id].get('name', 'Пользователь')
    
    banlist[target_id] = {
        "reason": reason,
        "date": datetime.now().isoformat(),
        "banned_by": user_id
    }
    save_all()
    
    await message.answer(
        f"✅ **Пользователь забанен!**\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID: `{target_id}`\n"
        f"📝 Причина: {reason}"
    )
    
    try:
        await bot.send_message(
            int(target_id),
            f"🚫 **Вы забанены.**\n\n"
            f"📝 Причина: {reason}\n\n"
            f"Если вы считаете, что это ошибка, напишите в поддержку."
        )
    except:
        pass

# ========== КОМАНДА /UNBAN ==========
async def cmd_unban(
    message: types.Message, users, banlist, save_all, bot,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только ГЛ.АДМИН может разбанивать.")
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /unban [ID]")
        return
    
    target_id = args[0]
    
    if target_id not in banlist:
        await message.answer("❌ Пользователь не в бане.")
        return
    
    user_name = users.get(target_id, {}).get('name', 'Пользователь')
    
    del banlist[target_id]
    save_all()
    
    await message.answer(
        f"✅ **Пользователь разбанен!**\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"🆔 ID: `{target_id}`"
    )
    
    try:
        await bot.send_message(
            int(target_id),
            f"✅ **Вы разбанены.**\n\n"
            f"Можете снова пользоваться ботом."
        )
    except:
        pass

# ========== КОМАНДА /SUPPORT (СПИСОК ЗАПРОСОВ) ==========
async def cmd_support_list(
    message: types.Message, support_requests, users,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        return
    
    if not support_requests:
        await message.answer("📭 Нет запросов в поддержку.")
        return
    
    text = "🆘 **Запросы в тех.поддержку:**\n\n"
    count = 0
    
    for rid, data in list(support_requests.items())[-20:]:
        status = "✅" if data.get("status") == "решен" else "⏳"
        user_name = data.get('user_name', 'Неизвестно')
        
        text += f"{status} ID: `{rid}`\n"
        text += f"   От: {user_name}\n"
        text += f"   Вопрос: {data['question'][:50]}...\n\n"
        count += 1
    
    text += f"\n📌 Используйте `/support [ID]` для просмотра деталей."
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /SUPPORT [ID] ==========
async def cmd_support_detail(
    message: types.Message, support_requests,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await cmd_support_list(message, support_requests, None, is_gl_admin, OWNER_ID)
        return
    
    request_id = args[0]
    
    if request_id not in support_requests:
        await message.answer("❌ Запрос не найден.")
        return
    
    data = support_requests[request_id]
    status_text = "✅ Решен" if data.get("status") == "решен" else "⏳ В обработке"
    
    text = f"🆘 **Запрос #{request_id}**\n\n"
    text += f"**Статус:** {status_text}\n"
    text += f"**От:** {data['user_name']}\n"
    text += f"**ID пользователя:** `{data['user_id']}`\n"
    text += f"**Дата:** {data['date'][:19]}\n\n"
    text += f"**Вопрос:**\n{data['question']}\n\n"
    
    if data.get("answer"):
        text += f"**Ответ:**\n{data['answer']}\n\n"
    
    text += "**Команды:**\n"
    text += f"`/answer {request_id} [текст]` - ответить\n"
    text += f"`/resolve {request_id}` - пометить решенным"
    
    await message.answer(text, parse_mode="Markdown")

# ========== КОМАНДА /ANSWER ==========
async def cmd_answer(
    message: types.Message, support_requests, save_all, bot,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        return
    
    text = message.get_args()
    if not text:
        await message.answer("❌ Использование: /answer [ID] [текст ответа]")
        return
    
    parts = text.split(maxsplit=1)
    request_id = parts[0]
    answer_text = parts[1] if len(parts) > 1 else ""
    
    if not answer_text:
        await message.answer("❌ Напишите текст ответа.")
        return
    
    if request_id not in support_requests:
        await message.answer("❌ Запрос не найден.")
        return
    
    data = support_requests[request_id]
    data["answer"] = answer_text
    data["status"] = "решен"
    data["answered_by"] = user_id
    data["answered_at"] = datetime.now().isoformat()
    save_all()
    
    await message.answer(f"✅ Ответ отправлен по запросу #{request_id}")
    
    try:
        await bot.send_message(
            int(data['user_id']),
            f"📨 **Ответ от тех.поддержки**\n\n"
            f"**Ваш вопрос:**\n{data['question']}\n\n"
            f"**Ответ:**\n{answer_text}"
        )
    except:
        pass

# ========== КОМАНДА /RESOLVE ==========
async def cmd_resolve(
    message: types.Message, support_requests, save_all,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /resolve [ID]")
        return
    
    request_id = args[0]
    
    if request_id not in support_requests:
        await message.answer("❌ Запрос не найден.")
        return
    
    support_requests[request_id]["status"] = "решен"
    save_all()
    
    await message.answer(f"✅ Запрос #{request_id} помечен как решенный.")

# ========== КОМАНДА /BROADCAST (НАЧАЛО РАССЫЛКИ) ==========
async def cmd_broadcast(message: types.Message, state: FSMContext, is_gl_admin, OWNER_ID):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только ГЛ.АДМИН может делать рассылку.")
        return
    
    await AdminStates.waiting_for_broadcast_text.set()
    await message.answer(
        "📝 **Рассылка**\n\n"
        "Введите текст для рассылки:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))
    )

# ========== ОБРАБОТКА ТЕКСТА РАССЫЛКИ ==========
async def process_broadcast_text(message: types.Message, state: FSMContext, bot, users, banlist):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("❌ Рассылка отменена.")
        return
    
    await state.update_data(broadcast_text=message.text)
    await AdminStates.waiting_for_broadcast_buttons.set()
    
    await message.answer(
        "🔗 **Добавьте кнопки (до 2-х)**\n\n"
        "Формат: `Текст1|URL1;Текст2|URL2`\n"
        "Пример: `Канал|https://t.me/channel;Сайт|https://site.com`\n\n"
        "Или отправьте `пропустить` чтобы продолжить без кнопок:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("пропустить"),
            KeyboardButton("❌ Отмена")
        )
    )

# ========== ОБРАБОТКА КНОПОК РАССЫЛКИ ==========
async def process_broadcast_buttons(message: types.Message, state: FSMContext, bot, users, banlist):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("❌ Рассылка отменена.")
        return
    
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    keyboard = None
    
    if message.text != "пропустить":
        try:
            buttons_data = message.text.split(';')
            inline_kb = InlineKeyboardMarkup(row_width=2)
            for btn in buttons_data[:2]:
                btn_text, btn_url = btn.split('|')
                inline_kb.add(InlineKeyboardButton(btn_text.strip(), url=btn_url.strip()))
            keyboard = inline_kb
        except:
            await message.answer("❌ Неправильный формат. Попробуйте еще раз или отправьте 'пропустить'")
            return
    
    await message.answer("⏳ Начинаю рассылку...")
    
    sent = 0
    failed = 0
    
    for uid in users.keys():
        if uid in banlist:
            failed += 1
            continue
        
        try:
            await bot.send_message(int(uid), broadcast_text, reply_markup=keyboard)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    
    await message.answer(
        f"✅ **Рассылка завершена!**\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}"
    )
    await state.finish()

# ========== КОМАНДА /ENDO ==========
async def cmd_endo(
    message: types.Message, dialogs, save_all,
    is_gl_admin, OWNER_ID
):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and user_id != OWNER_ID:
        await message.answer("❌ Только ГЛ.АДМИН может завершать чужие диалоги.")
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ Использование: /endo [ID админа]")
        return
    
    target_admin_id = args[0]
    
    user_to_remove = None
    for uid, aid in dialogs.items():
        if aid == target_admin_id:
            user_to_remove = uid
            break
    
    if not user_to_remove:
        await message.answer("❌ У этого админа нет активного диалога.")
        return
    
    del dialogs[user_to_remove]
    save_all()
    
    await message.answer(f"✅ Диалог админа {target_admin_id} завершён.")

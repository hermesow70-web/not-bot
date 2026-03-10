#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль диалогов - оптимизированная версия
"""

import asyncio
from datetime import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ========== СОСТОЯНИЯ ==========
class DialogStates(StatesGroup):
    waiting_for_tag = State()
    in_dialog = State()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📞 Позвать админа"))
    kb.add(KeyboardButton("🆘 Тех.поддержка"))
    return kb

def call_admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎲 Рандомно"))
    kb.add(KeyboardButton("🔍 По тегу"))
    kb.add(KeyboardButton("◀️ Назад"))
    return kb

def cancel_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

def dialog_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершить диалог"))
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Взять диалог"))
    kb.add(KeyboardButton("🆘 Запросы поддержки"))
    kb.add(KeyboardButton("👑 Админ-панель"))
    return kb

# ========== ТАЙМЕР ==========
async def queue_timeout(user_id, bot, dialogs, waiting_queue, save_all):
    await asyncio.sleep(600)
    if str(user_id) in dialogs:
        return
    if user_id in waiting_queue:
        waiting_queue.remove(user_id)
        save_all()
        try:
            await bot.send_message(user_id, "⏰ Админы заняты. Попробуйте позже.")
        except:
            pass

# ========== КНОПКИ ПОЛЬЗОВАТЕЛЯ ==========
async def user_call_admin(message: types.Message):
    await message.answer(
        "❓ Хотите позвать рандомно или того админа, которого больше предпочитаете?\n\n"
        "🔐 *Все диалоги скрыты, чтобы подать жалобу, обратитесь в группу в нашем канале*",
        parse_mode="Markdown",
        reply_markup=call_admin_menu()
    )

async def user_call_random(
    message: types.Message, bot, users, admins, dialogs, waiting_queue, save_all,
    is_banned, get_user_name
):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть диалог.")
        return
    
    waiting_queue.append(user_id)
    save_all()
    
    await message.answer(
        "⏳ Вы в очереди. Как только освободится админ, он к вам подключится.",
        reply_markup=cancel_menu()
    )
    
    asyncio.create_task(queue_timeout(user_id, bot, dialogs, waiting_queue, save_all))
    
    for admin_id in admins.keys():
        try:
            await bot.send_message(
                int(admin_id),
                f"👤 Пользователь {get_user_name(user_id)} ищет админа (рандомный вызов)."
            )
        except:
            pass

async def user_call_by_tag(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть диалог.")
        return
    
    await DialogStates.waiting_for_tag.set()
    await message.answer(
        "🔍 Введите тег админа (например #дил):",
        reply_markup=cancel_menu()
    )

async def process_admin_tag(
    message: types.Message, state: FSMContext,
    bot, admins, dialogs, pending_by_tag, save_all,
    get_user_name
):
    tag = message.text.strip()
    user_id = message.from_user.id
    
    if tag == "❌ Отмена":
        await state.finish()
        await message.answer("Меню:", reply_markup=main_menu())
        return
    
    admin_id = None
    for aid, data in admins.items():
        if data.get("tag") == tag:
            admin_id = aid
            break
    
    if not admin_id:
        await message.answer("❌ Админ с таким тегом не найден.")
        await state.finish()
        return
    
    if admin_id in dialogs.values():
        await message.answer("❌ Этот админ сейчас занят.")
        await state.finish()
        return
    
    if admin_id not in pending_by_tag:
        pending_by_tag[admin_id] = []
    
    if user_id not in pending_by_tag[admin_id]:
        pending_by_tag[admin_id].append(user_id)
        save_all()
    
    await message.answer(f"✅ Запрос отправлен админу {tag}")
    await state.finish()
    
    try:
        await bot.send_message(
            int(admin_id),
            f"👤 Пользователь {get_user_name(user_id)} позвал вас в диалог (тег {tag})."
        )
    except:
        pass

# ========== КНОПКИ АДМИНА ==========
async def admin_take_dialog_list(
    message: types.Message, waiting_queue, pending_by_tag, get_user_name, is_admin
):
    admin_id = str(message.from_user.id)
    
    if not is_admin(message.from_user.id):
        return
    
    text = "📋 **Ожидающие диалоги:**\n\n"
    
    if waiting_queue:
        text += "🎲 **Рандомные:**\n"
        for i, uid in enumerate(waiting_queue, 1):
            text += f"{i}. {get_user_name(uid)}\n"
    else:
        text += "🎲 Рандомных вызовов нет\n"
    
    if admin_id in pending_by_tag and pending_by_tag[admin_id]:
        text += "\n🔍 **По тегу для вас:**\n"
        for i, uid in enumerate(pending_by_tag[admin_id], 1):
            text += f"{i}. {get_user_name(uid)}\n"
    else:
        text += "\n🔍 Вызовов по тегу нет"
    
    await message.answer(text)

async def admin_take_random(
    message: types.Message, state: FSMContext,
    bot, dialogs, waiting_queue, save_all,
    get_user_name, get_admin_tag
):
    admin_id = message.from_user.id
    
    if not waiting_queue:
        await message.answer("📭 Нет пользователей в очереди.")
        return
    
    user_id = waiting_queue.pop(0)
    dialogs[str(user_id)] = str(admin_id)
    save_all()
    
    admin_tag = get_admin_tag(admin_id)
    
    try:
        await bot.send_message(
            user_id,
            f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
            reply_markup=dialog_menu()
        )
    except:
        pass
    
    await message.answer(
        f"✅ Вы подключились к пользователю {get_user_name(user_id)}",
        reply_markup=dialog_menu()
    )
    await DialogStates.in_dialog.set()

async def admin_take_by_tag(
    message: types.Message, state: FSMContext,
    bot, dialogs, pending_by_tag, save_all,
    get_user_name, get_admin_tag
):
    admin_id = str(message.from_user.id)
    
    if admin_id not in pending_by_tag or not pending_by_tag[admin_id]:
        await message.answer("📭 Нет пользователей, которые позвали вас по тегу.")
        return
    
    user_id = pending_by_tag[admin_id].pop(0)
    dialogs[str(user_id)] = str(admin_id)
    save_all()
    
    admin_tag = get_admin_tag(int(admin_id))
    
    try:
        await bot.send_message(
            user_id,
            f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
            reply_markup=dialog_menu()
        )
    except:
        pass
    
    await message.answer(
        f"✅ Вы подключились к пользователю {get_user_name(user_id)}",
        reply_markup=dialog_menu()
    )
    await DialogStates.in_dialog.set()

# ========== ОБРАБОТКА ДИАЛОГОВ ==========
async def handle_dialog_messages(
    message: types.Message, state: FSMContext,
    bot, dialogs, save_all,
    is_admin, get_user_name, get_admin_tag
):
    user_id = message.from_user.id
    text = message.text
    
    if str(user_id) in dialogs:
        admin_id = int(dialogs[str(user_id)])
        
        if text == "🔚 Завершить диалог":
            del dialogs[str(user_id)]
            save_all()
            
            try:
                await bot.send_message(admin_id, "🔚 Пользователь завершил диалог.")
            except:
                pass
            
            await message.answer(
                "✅ **Диалог завершён.**\n\n"
                "Если админ был к вам невежлив, груб или нарушил правила, "
                "напишите #крип и опишите ситуацию. Ваша жалоба будет рассмотрена.",
                reply_markup=main_menu()
            )
            await state.finish()
            return
        
        user_name = get_user_name(user_id)
        try:
            await bot.send_message(admin_id, f"{user_name}\n{text}")
        except:
            await message.answer("❌ Не удалось отправить сообщение.")
        return
    
    for uid, aid in dialogs.items():
        if aid == str(user_id):
            if text == "🔚 Завершить диалог":
                del dialogs[uid]
                save_all()
                
                try:
                    await bot.send_message(
                        int(uid),
                        "🔚 **Администратор завершил диалог.**\n\n"
                        "Если админ был к вам невежлив, груб или нарушил правила, "
                        "напишите #крип и опишите ситуацию. Ваша жалоба будет рассмотрена."
                    )
                except:
                    pass
                
                await message.answer("✅ Диалог завершён.", reply_markup=admin_menu())
                await state.finish()
                return
            
            admin_tag = get_admin_tag(int(user_id))
            try:
                await bot.send_message(int(uid), f"{admin_tag}\n{text}")
            except:
                await message.answer("❌ Не удалось отправить сообщение.")
            return
    
    if is_admin(user_id):
        await message.answer("Меню:", reply_markup=admin_menu())
    else:
        await message.answer("Меню:", reply_markup=main_menu())

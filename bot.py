#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor

# ========== ТВОИ ДАННЫЕ ==========
BOT_TOKEN = "8678152372:AAHEqZ5Lxe6CsSZpX0loPyOioejOFYCTtoI"
OWNER_ID = 8402407852
OWNER_TAG = "#крип"
CHANNEL_LINK = "https://t.me/+arKuZnc9R9hhNDIx"
# =================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ========== РАБОТА С ФАЙЛАМИ ==========
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def load_data(filename: str):
    try:
        with open(DATA_DIR / f"{filename}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if filename == "queue":
            return []
        return {}

def save_data(filename: str, data):
    with open(DATA_DIR / f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ========== ДАННЫЕ ==========
users = load_data("users")
admins = load_data("admins")
dialogs = load_data("dialogs")
waiting_queue = load_data("queue")
pending_by_tag = load_data("pending_by_tag")
banlist = load_data("banlist")
complaints = load_data("complaints")

if str(OWNER_ID) not in admins:
    admins[str(OWNER_ID)] = {
        "tag": OWNER_TAG,
        "role": "ГЛ.АДМИН",
        "date": datetime.now().isoformat()
    }
    save_data("admins", admins)

def save_all():
    save_data("users", users)
    save_data("admins", admins)
    save_data("dialogs", dialogs)
    save_data("queue", waiting_queue)
    save_data("pending_by_tag", pending_by_tag)
    save_data("banlist", banlist)
    save_data("complaints", complaints)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def is_admin(user_id: int) -> bool:
    return str(user_id) in admins

def is_gl_admin(user_id: int) -> bool:
    if str(user_id) not in admins:
        return False
    return admins[str(user_id)].get("role") == "ГЛ.АДМИН"

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_banned(user_id: int) -> bool:
    return str(user_id) in banlist

def get_user_name(user_id: int) -> str:
    return users.get(str(user_id), {}).get("name", "Пользователь")

def get_admin_tag(user_id: int) -> str:
    return admins.get(str(user_id), {}).get("tag", "#unknown")

# ========== ИМПОРТ МОДУЛЕЙ ==========
from dialogs import (
    main_menu, admin_menu, dialog_menu, cancel_menu, channel_keyboard,
    DialogStates, queue_timeout,
    user_call_random, user_call_by_tag, process_admin_tag,
    admin_dialog_list, admin_take_dialog, process_admin_choice,
    handle_dialog_messages
)

from admin_panel import (
    BroadcastStates,
    cmd_list, cmd_adlist, cmd_complaints,
    cmd_setadmin, cmd_deladmin, cmd_ban, cmd_unban, cmd_endo,
    cmd_all, process_broadcast_text, process_broadcast_buttons
)

# ========== ЖАЛОБЫ #КРИП ==========
@dp.message_handler(lambda message: message.text and message.text.startswith('#крип'))
async def handle_crip(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    complaint_id = str(len(complaints) + 1)
    complaints[complaint_id] = {
        "user_id": user_id,
        "user_name": get_user_name(user_id),
        "text": text,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer("✅ Ваша жалоба отправлена ГЛ.АДМИНАМ.")
    
    for aid, data in admins.items():
        if data.get("role") == "ГЛ.АДМИН" or int(aid) == OWNER_ID:
            try:
                await bot.send_message(
                    int(aid),
                    f"⚠️ **ЖАЛОБА**\n\nОт: {get_user_name(user_id)} (ID: {user_id})\nТекст: {text}"
                )
            except:
                pass

# ========== СТАРТ ==========
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    await state.finish()
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    if str(user_id) not in users:
        await state.set_state(DialogStates.waiting_for_name)
        
        await message.answer(
            "👋 *Здравствуй, хочешь тёплого общения? Внимания?*\n\n"
            "❌ *ЗАБУДЬ ДРУГИХ БОТОВ!*\n"
            "✅ *У нас всё по другому, хороший функционал и без ответа ты точно не останешься!*\n\n"
            "🔐 *У НАС НИКТО НЕ ВИДИТ ДИАЛОГИ, ПОЛНАЯ АНОНИМНОСТЬ*\n"
            "*(диалоги может посмотреть только владелец и то если будет жалоба)*\n\n"
            "✨ *ПРИЯТНОГО ВАМ ОБЩЕНИЯ!*",
            parse_mode="Markdown"
        )
        
        await message.answer(
            "Если не сложно подпишись на наш канал, это НЕОБЯЗАТЕЛЬНО но нам будет приятно)",
            reply_markup=channel_keyboard()
        )
        
        await message.answer("📝 Как вас зовут?")
        return
    
    if str(user_id) in dialogs:
        admin_id = dialogs[str(user_id)]
        if admin_id not in admins:
            del dialogs[str(user_id)]
            save_all()
        else:
            admin_tag = get_admin_tag(int(admin_id))
            await message.answer(
                f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
                reply_markup=dialog_menu()
            )
            return
    
    if is_admin(user_id):
        await message.answer("Меню администратора:", reply_markup=admin_menu())
    else:
        await message.answer("Выберите действие:", reply_markup=main_menu())

# ========== ОБРАБОТКА ИМЕНИ ==========
@dp.message_handler(state=DialogStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if not name:
        await message.answer("❌ Имя не может быть пустым. Введите имя:")
        return
    
    users[str(user_id)] = {
        "name": name,
        "username": message.from_user.username,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Приятно познакомиться, {name}!")
    await state.finish()
    
    if is_admin(user_id):
        await message.answer("Меню администратора:", reply_markup=admin_menu())
    else:
        await message.answer("Выберите действие:", reply_markup=main_menu())

# ========== КОМАНДА /END ==========
@dp.message_handler(commands=['end'])
async def cmd_end(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    
    if user_id_str in dialogs:
        admin_id = int(dialogs[user_id_str])
        del dialogs[user_id_str]
        save_all()
        
        try:
            await bot.send_message(admin_id, "🔚 Пользователь завершил диалог.", reply_markup=admin_menu())
        except:
            pass
        
        await message.answer(
            "✅ Диалог завершён.\n\n"
            "Если админ был к вам невежлив, груб или нарушил правила, "
            "напишите #крип и опишите ситуацию. Ваша жалоба будет рассмотрена."
        )
        
        await state.finish()
        
        if is_admin(user_id):
            await message.answer("Меню:", reply_markup=admin_menu())
        else:
            await message.answer("Главное меню:", reply_markup=main_menu())
        return
    
    for uid, aid in dialogs.items():
        if aid == user_id_str:
            del dialogs[uid]
            save_all()
            
            try:
                await bot.send_message(
                    int(uid),
                    "🔚 Администратор завершил диалог.\n\n"
                    "Если админ был к вам невежлив, груб или нарушил правила, "
                    "напишите #крип и опишите ситуацию. Ваша жалоба будет рассмотрена."
                )
            except:
                pass
            
            await message.answer("✅ Диалог завершён.")
            await state.finish()
            await message.answer("Меню:", reply_markup=admin_menu())
            return
    
    await message.answer("❌ У вас нет активного диалога.")

# ========== КОМАНДА /HELP ==========
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    
    text = "📋 **Команды:**\n"
    text += "`/start` - Начать\n"
    text += "`/end` - Завершить диалог\n"
    
    if is_admin(user_id):
        text += "`/admin` - Панель администратора\n"
    
    await message.answer(text)

# ========== КОМАНДА /ADMIN ==========
@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    text = (
        "👑 **Команды администратора:**\n\n"
        "`/list` - список пользователей\n"
        "`/adlist` - список админов\n"
    )
    
    if is_gl_admin(user_id) or is_owner(user_id):
        text += (
            "\n👑 **Команды ГЛ.АДМИНА:**\n\n"
            "`/setadmin [ID] [тег] [роль]` - выдать админку\n"
            "`/deladmin [ID]` - удалить админа\n"
            "`/ban [ID]` - забанить\n"
            "`/unban [ID]` - разбанить\n"
            "`/complaints` - жалобы #крип\n"
            "`/all` - рассылка\n"
            "`/endo [ID]` - завершить диалог админа"
        )
    
    await message.answer(text, parse_mode="Markdown")

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message_handler(lambda message: message.text == "👑 Админ-панель")
async def admin_panel_button(message: types.Message):
    user_id = message.from_user.id
    
    if not is_gl_admin(user_id) and not is_owner(user_id):
        await message.answer("❌ Только для ГЛ.АДМИНОВ.")
        return
    
    await cmd_admin(message)

# ========== РЕГИСТРАЦИЯ КОМАНД ==========
dp.register_message_handler(lambda msg: cmd_list(msg, users, banlist, is_admin), commands=['list'])
dp.register_message_handler(lambda msg: cmd_adlist(msg, users, admins, is_admin), commands=['adlist'])
dp.register_message_handler(lambda msg: cmd_complaints(msg, complaints, is_gl_admin, is_owner, OWNER_ID), commands=['complaints'])
dp.register_message_handler(lambda msg: cmd_setadmin(msg, users, admins, save_all, is_gl_admin, is_owner, OWNER_ID), commands=['setadmin'])
dp.register_message_handler(lambda msg: cmd_deladmin(msg, admins, save_all, is_gl_admin, is_owner, OWNER_ID), commands=['deladmin'])
dp.register_message_handler(lambda msg: cmd_ban(msg, users, admins, banlist, save_all, is_gl_admin, is_owner, OWNER_ID), commands=['ban'])
dp.register_message_handler(lambda msg: cmd_unban(msg, banlist, save_all, is_gl_admin, is_owner, OWNER_ID), commands=['unban'])
dp.register_message_handler(lambda msg: cmd_endo(msg, dialogs, save_all, is_gl_admin, is_owner, OWNER_ID), commands=['endo'])
dp.register_message_handler(lambda msg, state: cmd_all(msg, state, is_gl_admin, is_owner, OWNER_ID), commands=['all'], state='*')

dp.register_message_handler(
    lambda msg, state: process_broadcast_text(msg, state, bot, users, banlist), 
    state=BroadcastStates.waiting_for_text
)
dp.register_message_handler(
    lambda msg, state: process_broadcast_buttons(msg, state, bot, users, banlist), 
    state=BroadcastStates.waiting_for_buttons
)

# ========== КНОПКИ ИЗ DIALOGS ==========
dp.register_message_handler(
    lambda msg: user_call_random(msg, bot, users, admins, dialogs, waiting_queue, save_all, is_banned, get_user_name),
    lambda message: message.text == "🎲 Позвать рандомно"
)

dp.register_message_handler(
    lambda msg, state: user_call_by_tag(msg, state, is_banned, dialogs),
    lambda message: message.text == "🔍 Позвать админа (по тегу)"
)

dp.register_message_handler(
    lambda msg, state: process_admin_tag(msg, state, bot, admins, dialogs, pending_by_tag, save_all, get_user_name),
    state=DialogStates.user_waiting_tag
)

dp.register_message_handler(
    lambda msg: admin_dialog_list(msg, is_admin, waiting_queue, get_user_name),
    lambda

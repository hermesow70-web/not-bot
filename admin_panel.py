import asyncio
from datetime import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ========== СОСТОЯНИЯ ==========
class BroadcastStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_buttons = State()

# ========== КОМАНДА /LIST ==========
async def cmd_list(message: types.Message, users, banlist, is_admin):
    if not is_admin(message.from_user.id):
        return
    
    text = "📋 **Все пользователи:**\n\n"
    for uid, data in users.items():
        name = data.get('name', 'Неизвестно')
        banned = " 🔴 ЗАБАНЕН" if uid in banlist else ""
        text += f"👤 {name} | ID: {uid}{banned}\n"
    
    await message.answer(text)

# ========== КОМАНДА /ADLIST ==========
async def cmd_adlist(message: types.Message, users, admins, is_admin):
    if not is_admin(message.from_user.id):
        return
    
    text = "👑 **Все администраторы:**\n\n"
    for uid, data in admins.items():
        user_data = users.get(uid, {})
        name = user_data.get('name', 'Неизвестно')
        text += f"👤 {name} | {data['tag']} | {data['role']} | ID: {uid}\n"
    
    await message.answer(text)

# ========== КОМАНДА /COMPLAINTS ==========
async def cmd_complaints(message: types.Message, complaints, is_gl_admin, is_owner, OWNER_ID):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    
    if not complaints:
        await message.answer("📭 Нет жалоб.")
        return
    
    text = "⚠️ **Жалобы #крип:**\n\n"
    for cid, data in complaints.items():
        text += f"ID: {cid}\n"
        text += f"От: {data['user_name']} (ID: {data['user_id']})\n"
        text += f"Текст: {data['text']}\n"
        text += f"Дата: {data['date'][:19]}\n\n"
    
    await message.answer(text)

# ========== КОМАНДА /SETADMIN ==========
async def cmd_setadmin(message: types.Message, users, admins, save_all, is_gl_admin, is_owner, OWNER_ID):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    
    args = message.get_args().split()
    if len(args) < 3:
        await message.answer("❌ /setadmin [ID] [тег] [роль]\nРоли: АДМИН или ГЛ.АДМИН")
        return
    
    target_id, tag, role = args[0], args[1], args[2].upper()
    
    if role not in ["АДМИН", "ГЛ.АДМИН"]:
        await message.answer("❌ Роль должна быть АДМИН или ГЛ.АДМИН")
        return
    
    if target_id not in users:
        await message.answer("❌ Пользователь с таким ID не найден.")
        return
    
    for data in admins.values():
        if data.get("tag") == tag:
            await message.answer("❌ Такой тег уже существует.")
            return
    
    admins[target_id] = {
        "tag": tag,
        "role": role,
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Админка выдана!\nID: {target_id}\nТег: {tag}\nРоль: {role}")

# ========== КОМАНДА /DELADMIN ==========
async def cmd_deladmin(message: types.Message, admins, save_all, is_gl_admin, is_owner, OWNER_ID):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /deladmin [ID]")
        return
    
    target_id = args[0]
    
    if target_id not in admins:
        await message.answer("❌ Админ с таким ID не найден.")
        return
    
    if target_id == str(OWNER_ID):
        await message.answer("❌ Нельзя удалить владельца.")
        return
    
    tag = admins[target_id]["tag"]
    del admins[target_id]
    save_all()
    
    await message.answer(f"✅ Админ {target_id} ({tag}) удалён.")

# ========== КОМАНДА /BAN ==========
async def cmd_ban(message: types.Message, users, admins, banlist, save_all, is_gl_admin, is_owner, OWNER_ID):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /ban [ID]")
        return
    
    target_id = args[0]
    
    if target_id not in users:
        await message.answer("❌ Пользователь с таким ID не найден.")
        return
    
    if target_id in admins:
        await message.answer("❌ Нельзя забанить администратора.")
        return
    
    banlist[target_id] = {
        "reason": "Бан от администратора",
        "date": datetime.now().isoformat()
    }
    save_all()
    
    await message.answer(f"✅ Пользователь {target_id} забанен.")

# ========== КОМАНДА /UNBAN ==========
async def cmd_unban(message: types.Message, banlist, save_all, is_gl_admin, is_owner, OWNER_ID):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /unban [ID]")
        return
    
    target_id = args[0]
    
    if target_id not in banlist:
        await message.answer("❌ Пользователь не в бане.")
        return
    
    del banlist[target_id]
    save_all()
    
    await message.answer(f"✅ Пользователь {target_id} разбанен.")

# ========== КОМАНДА /ENDO ==========
async def cmd_endo(message: types.Message, dialogs, save_all, is_gl_admin, is_owner, OWNER_ID):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        return
    
    args = message.get_args().split()
    if len(args) < 1:
        await message.answer("❌ /endo [ID админа]")
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

# ========== КОМАНДА /ALL (РАССЫЛКА) ==========
async def cmd_all(message: types.Message, state: FSMContext, is_gl_admin, is_owner, OWNER_ID):
    if not is_gl_admin(message.from_user.id) and not is_owner(message.from_user.id):
        await message.answer("❌ Только ГЛ.АДМИН может делать рассылку.")
        return
    
    await BroadcastStates.waiting_for_text.set()
    await message.answer(
        "📝 Введите текст для рассылки:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))
    )

async def process_broadcast_text(message: types.Message, state: FSMContext, bot, users, banlist):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено")
        return
    
    await state.update_data(broadcast_text=message.text)
    await BroadcastStates.waiting_for_buttons.set()
    
    await message.answer(
        "🔗 Добавьте кнопки (до 2-х). Формат: Текст1|URL1;Текст2|URL2\n"
        "Или отправьте 'пропустить' чтобы продолжить без кнопок",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(
            KeyboardButton("пропустить"),
            KeyboardButton("❌ Отмена")
        )
    )

async def process_broadcast_buttons(message: types.Message, state: FSMContext, bot, users, banlist):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено")
        return
    
    data = await state.get_data()
    text = data.get("broadcast_text")
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
    for uid in users:
        if uid in banlist:
            continue
        try:
            await bot.send_message(int(uid), text, reply_markup=keyboard)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    
    await message.answer(f"✅ Рассылка завершена! Отправлено {sent} пользователям")
    await state.finish()

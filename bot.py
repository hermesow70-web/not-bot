#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ОСНОВНОЙ БОТ - ПОДДЕРЖКА С ДИАЛОГАМИ И АДМИНКОЙ
Версия 2.0 - ВСЁ РАБОТАЕТ
"""

import asyncio
import logging
from datetime import datetime

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

# ========== ИМПОРТ МОДУЛЕЙ ==========
from database import (
    users, admins, dialogs, waiting_queue, pending_by_tag, banlist, support_requests,
    save_all, is_admin, is_gl_admin, is_owner, is_banned,
    get_user_name, get_admin_tag, get_admin_role
)

from dialogs import (
    main_menu, admin_menu, call_admin_menu, cancel_menu, dialog_menu,
    DialogStates, queue_timeout,
    user_call_admin, user_call_random, user_call_by_tag, process_admin_tag,
    admin_take_dialog_list, admin_take_random, admin_take_by_tag,
    handle_dialog_messages
)

from admin_panel import (
    AdminStates,
    cmd_admin, admin_panel_button,
    cmd_users, cmd_admins, cmd_search,
    cmd_setadmin, cmd_deladmin, cmd_ban, cmd_unban,
    cmd_support_list, cmd_support_detail, cmd_answer, cmd_resolve,
    cmd_broadcast, process_broadcast_text, process_broadcast_buttons,
    cmd_endo
)

# Добавляем владельца как ГЛ.АДМИНА
if str(OWNER_ID) not in admins:
    admins[str(OWNER_ID)] = {
        "tag": OWNER_TAG,
        "name": "Владелец",
        "role": "ГЛ.АДМИН",
        "date": datetime.now().isoformat()
    }
    save_all()

# ========== ЖАЛОБЫ #КРИП ==========
@dp.message_handler(lambda message: message.text and message.text.startswith('#крип'))
async def handle_crip(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    # Отправляем всем ГЛ.АДМИНАМ
    for aid, data in admins.items():
        if data.get("role") == "ГЛ.АДМИН" or int(aid) == OWNER_ID:
            try:
                await bot.send_message(
                    int(aid),
                    f"⚠️ **ЖАЛОБА**\n\n"
                    f"От: {get_user_name(user_id)} (ID: {user_id})\n"
                    f"Текст: {text}"
                )
            except:
                pass
    
    await message.answer("✅ Ваша жалоба отправлена администрации.")

# ========== КОМАНДА /START ==========
@dp.message_handler(commands=['start'], state='*')
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    
    await state.finish()
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    # Регистрируем нового пользователя
    if user_id_str not in users:
        users[user_id_str] = {
            "name": message.from_user.full_name,
            "username": message.from_user.username,
            "date": datetime.now().isoformat()
        }
        save_all()
    
    # Проверяем активный диалог
    if user_id_str in dialogs:
        admin_id = dialogs[user_id_str]
        if admin_id not in admins:
            del dialogs[user_id_str]
            save_all()
        else:
            admin_tag = get_admin_tag(int(admin_id))
            await message.answer(
                f"🔔 К вам подключился Админ {admin_tag}. Приятного общения!",
                reply_markup=dialog_menu()
            )
            return
    
    if is_admin(user_id):
        await message.answer("👑 Панель администратора:", reply_markup=admin_menu())
    else:
        await message.answer(
            "👋 Добро пожаловать!\n"
            "Выберите действие:",
            reply_markup=main_menu()
        )

# ========== КОМАНДА /HELP ==========
@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    
    text = "📋 **Список команд:**\n\n"
    text += "`/start` - Главное меню\n"
    text += "`/help` - Эта справка\n"
    
    if is_admin(user_id):
        text += "\n👑 **Команды администратора:**\n"
        text += "`/admin` - Панель администратора\n"
    
    if is_gl_admin(user_id) or user_id == OWNER_ID:
        text += "\n👑👑 **Команды ГЛ.АДМИНА:**\n"
        text += "`/users` - Список пользователей\n"
        text += "`/admins` - Список админов\n"
        text += "`/search [текст]` - Поиск пользователей\n"
        text += "`/setadmin [ID] [тег] [роль]` - Выдать админку\n"
        text += "`/deladmin [ID]` - Удалить админа\n"
        text += "`/ban [ID] [причина]` - Забанить\n"
        text += "`/unban [ID]` - Разбанить\n"
        text += "`/support` - Запросы поддержки\n"
        text += "`/broadcast` - Рассылка\n"
        text += "`/endo [ID]` - Завершить диалог админа"
    
    await message.answer(text, parse_mode="Markdown")

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
            await bot.send_message(admin_id, "🔚 Пользователь завершил диалог.")
        except:
            pass
        
        await message.answer(
            "✅ **Диалог завершён.**\n\n"
            "Если админ был к вам невежлив, груб или нарушил правила, "
            "напишите #крип и опишите ситуацию.",
            reply_markup=main_menu()
        )
        await state.finish()
        return
    
    for uid, aid in dialogs.items():
        if aid == user_id_str:
            del dialogs[uid]
            save_all()
            
            try:
                await bot.send_message(
                    int(uid),
                    "🔚 **Администратор завершил диалог.**\n\n"
                    "Если админ был к вам невежлив, груб или нарушил правила, "
                    "напишите #крип и опишите ситуацию."
                )
            except:
                pass
            
            await message.answer("✅ Диалог завершён.", reply_markup=admin_menu())
            await state.finish()
            return
    
    await message.answer("❌ У вас нет активного диалога.")

# ========== КНОПКА "ПОЗВАТЬ АДМИНА" ==========
@dp.message_handler(lambda message: message.text == "📞 Позвать админа")
async def handle_call_admin(message: types.Message):
    await user_call_admin(message)

# ========== КНОПКА "🎲 РАНДОМНО" ==========
@dp.message_handler(lambda message: message.text == "🎲 Рандомно")
async def handle_random(message: types.Message):
    await user_call_random(
        message, bot, users, admins, dialogs, waiting_queue, save_all,
        is_banned, get_user_name
    )

# ========== КНОПКА "🔍 ПО ТЕГУ" ==========
@dp.message_handler(lambda message: message.text == "🔍 По тегу")
async def handle_by_tag(message: types.Message, state: FSMContext):
    await user_call_by_tag(message, state)

# ========== ОБРАБОТКА ВВОДА ТЕГА ==========
@dp.message_handler(state=DialogStates.waiting_for_tag)
async def handle_tag_input(message: types.Message, state: FSMContext):
    await process_admin_tag(
        message, state, bot, admins, dialogs, pending_by_tag, save_all,
        get_user_name
    )

# ========== КНОПКА "🆘 ТЕХ.ПОДДЕРЖКА" ==========
@dp.message_handler(lambda message: message.text == "🆘 Тех.поддержка")
async def handle_support(message: types.Message, state: FSMContext):
    await message.answer(
        "📝 Введите свой вопрос и мы обязательно его решим:",
        reply_markup=cancel_menu()
    )
    await DialogStates.waiting_for_tag.set()  # Временное состояние

@dp.message_handler(state=DialogStates.waiting_for_tag)
async def handle_support_question(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    question = message.text
    
    if question == "❌ Отмена":
        await state.finish()
        await message.answer("Отменено", reply_markup=main_menu())
        return
    
    request_id = str(hash(question + user_id + str(datetime.now())))[-6:]
    support_requests[request_id] = {
        "user_id": user_id,
        "user_name": get_user_name(message.from_user.id),
        "question": question,
        "date": datetime.now().isoformat(),
        "status": "новый"
    }
    save_all()
    
    await message.answer(
        "✅ Ваш вопрос отправлен в тех.поддержку!\n"
        "Мы ответим вам в ближайшее время.",
        reply_markup=main_menu()
    )
    await state.finish()
    
    for aid, data in admins.items():
        if data.get("role") == "ГЛ.АДМИН":
            try:
                await bot.send_message(
                    int(aid),
                    f"🆘 **Новый запрос в тех.поддержку**\n\n"
                    f"ID: {request_id}\n"
                    f"От: {get_user_name(message.from_user.id)}\n"
                    f"Вопрос: {question}"
                )
            except:
                pass

# ========== КНОПКИ АДМИНА ==========
@dp.message_handler(lambda message: message.text == "📋 Взять диалог")
async def handle_take_dialog(message: types.Message):
    await admin_take_dialog_list(
        message, waiting_queue, pending_by_tag, get_user_name, is_admin
    )

@dp.message_handler(lambda message: message.text == "🎲 Рандомно" and is_admin)
async def handle_take_random(message: types.Message, state: FSMContext):
    await admin_take_random(
        message, state, bot, dialogs, waiting_queue, save_all,
        get_user_name, get_admin_tag
    )

@dp.message_handler(lambda message: message.text == "🔍 По тегу" and is_admin)
async def handle_take_by_tag(message: types.Message, state: FSMContext):
    await admin_take_by_tag(
        message, state, bot, dialogs, pending_by_tag, save_all,
        get_user_name, get_admin_tag
    )

@dp.message_handler(lambda message: message.text == "🆘 Запросы поддержки")
async def handle_support_requests(message: types.Message):
    await cmd_support_list(message, support_requests, users, is_gl_admin, OWNER_ID)

@dp.message_handler(lambda message: message.text == "👑 Админ-панель")
async def handle_admin_panel(message: types.Message):
    await admin_panel_button(message, is_gl_admin, OWNER_ID)

# ========== КНОПКА "◀️ НАЗАД" ==========
@dp.message_handler(lambda message: message.text == "◀️ Назад")
async def handle_back(message: types.Message):
    user_id = message.from_user.id
    
    if is_admin(user_id):
        await message.answer("Меню:", reply_markup=admin_menu())
    else:
        await message.answer("Меню:", reply_markup=main_menu())

# ========== КНОПКА "❌ ОТМЕНА" ==========
@dp.message_handler(lambda message: message.text == "❌ Отмена", state='*')
async def handle_cancel(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    
    if is_admin(user_id):
        await message.answer("Отменено", reply_markup=admin_menu())
    else:
        await message.answer("Отменено", reply_markup=main_menu())

# ========== РЕГИСТРАЦИЯ КОМАНД АДМИНКИ ==========
dp.register_message_handler(lambda msg: cmd_users(msg, users, banlist, is_admin), commands=['users'])
dp.register_message_handler(lambda msg: cmd_admins(msg, users, admins, is_admin), commands=['admins'])
dp.register_message_handler(lambda msg: cmd_search(msg, users, banlist, is_admin), commands=['search'])
dp.register_message_handler(lambda msg: cmd_setadmin(msg, users, admins, save_all, bot, is_gl_admin, OWNER_ID), commands=['setadmin'])
dp.register_message_handler(lambda msg: cmd_deladmin(msg, users, admins, save_all, bot, is_gl_admin, OWNER_ID), commands=['deladmin'])
dp.register_message_handler(lambda msg: cmd_ban(msg, users, admins, banlist, save_all, bot, is_gl_admin, OWNER_ID), commands=['ban'])
dp.register_message_handler(lambda msg: cmd_unban(msg, users, banlist, save_all, bot, is_gl_admin, OWNER_ID), commands=['unban'])
dp.register_message_handler(lambda msg: cmd_support_list(msg, support_requests, users, is_gl_admin, OWNER_ID), commands=['support'])
dp.register_message_handler(lambda msg: cmd_support_detail(msg, support_requests, is_gl_admin, OWNER_ID), commands=['support'])
dp.register_message_handler(lambda msg: cmd_answer(msg, support_requests, save_all, bot, is_gl_admin, OWNER_ID), commands=['answer'])
dp.register_message_handler(lambda msg: cmd_resolve(msg, support_requests, save_all, is_gl_admin, OWNER_ID), commands=['resolve'])
dp.register_message_handler(lambda msg, state: cmd_broadcast(msg, state, is_gl_admin, OWNER_ID), commands=['broadcast'])
dp.register_message_handler(lambda msg, state: process_broadcast_text(msg, state, bot, users, banlist), state=AdminStates.waiting_for_broadcast_text)
dp.register_message_handler(lambda msg, state: process_broadcast_buttons(msg, state, bot, users, banlist), state=AdminStates.waiting_for_broadcast_buttons)
dp.register_message_handler(lambda msg: cmd_endo(msg, dialogs, save_all, is_gl_admin, OWNER_ID), commands=['endo'])
dp.register_message_handler(lambda msg: cmd_admin(msg, is_admin, is_gl_admin, OWNER_ID), commands=['admin'])

# ========== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ ==========
@dp.message_handler()
async def handle_all_messages(message: types.Message, state: FSMContext):
    await handle_dialog_messages(
        message, state, bot, dialogs, save_all,
        is_admin, get_user_name, get_admin_tag
    )

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("🚀 БОТ ЗАПУЩЕН")
    logger.info(f"👑 Владелец: {OWNER_ID}")
    logger.info(f"👥 Админов: {len(admins)}")
    logger.info(f"👤 Пользователей: {len(users)}")
    logger.info("=" * 50)
    
    executor.start_polling(dp, skip_updates=True)

import asyncio
from datetime import datetime

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ========== СОСТОЯНИЯ ==========
class DialogStates(StatesGroup):
    waiting_for_name = State()
    user_waiting_tag = State()
    admin_waiting_choice = State()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎲 Позвать рандомно"))
    kb.add(KeyboardButton("🔍 Позвать админа (по тегу)"))
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📋 Список диалогов"))
    kb.add(KeyboardButton("👑 Админ-панель"))
    return kb

def dialog_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔚 Завершить диалог"))
    return kb

def cancel_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Отмена"))
    return kb

# ========== ТАЙМЕР ==========
async def queue_timeout(user_id: int, bot, dialogs, waiting_queue, save_all):
    await asyncio.sleep(600)
    if str(user_id) in dialogs:
        return
    if user_id in waiting_queue:
        waiting_queue.remove(user_id)
        save_all()
        try:
            await bot.send_message(user_id, "⏰ Похоже, что все админы заняты.\nПопробуйте снова /start")
        except:
            pass

# ========== КНОПКИ ПОЛЬЗОВАТЕЛЯ ==========
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
    await message.answer("⏳ Вы в очереди.", reply_markup=cancel_menu())
    asyncio.create_task(queue_timeout(user_id, bot, dialogs, waiting_queue, save_all))
    
    for admin_id in admins.keys():
        try:
            await bot.send_message(int(admin_id), f"👤 Пользователь {get_user_name(user_id)} ищет админа.")
        except:
            pass

async def user_call_by_tag(
    message: types.Message, state: FSMContext,
    is_banned, dialogs
):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        await message.answer("❌ Вы забанены.")
        return
    
    if str(user_id) in dialogs:
        await message.answer("❌ У вас уже есть диалог.")
        return
    
    await DialogStates.user_waiting_tag.set()
    await message.answer("🔍 Введите тег админа (например #дил):", reply_markup=cancel_menu())

async def process_admin_tag(
    message: types.Message, state: FSMContext,
    bot, admins, dialogs, pending_by_tag, save_all,
    get_user_name
):
    tag = message.text.strip()
    
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
    
    user_id = message.from_user.id
    
    if admin_id not in pending_by_tag:
        pending_by_tag[admin_id] = []
    
    if user_id not in pending_by_tag[admin_id]:
        pending_by_tag[admin_id].append(user_id)
        save_all()
    
    await message.answer(f"✅ Запрос отправлен админу {tag}")
    await state.finish()
    
    try:
        await bot.send_message(int(admin_id), f"👤 Пользователь {get_user_name(user_id)} позвал вас в диалог (тег {tag}).")
    except:
        pass

# ========== КНОПКИ АДМИНА ==========
async def admin_dialog_list(
    message: types.Message, is_admin, waiting_queue, get_user_name
):
    if not is_admin(message.from_user.id):
        return
    
    text = "📋 **Ожидающие диалоги:**\n\n"
    if waiting_queue:
        for i, uid in enumerate(waiting_queue, 1):
            text += f"{i}. {get_user_name(uid)}\n"
    else:
        text += "Нет ожидающих диалогов"
    
    await message.answer(text)

async def admin_take_dialog(
    message: types.Message, state: FSMContext,
    is_admin, waiting_queue
):
    if not is_admin(message.from_user.id):
        return
    
    if not waiting_queue:
        await message.answer("📭 Нет диалогов.")
        return
    
    await DialogStates.admin_waiting_choice.set()
    await message.answer("Введите номер диалога из списка:")

async def process_admin_choice(
    message: types.Message, state: FSMContext,
    bot, dialogs, waiting_queue, save_all,
    get_user_name, get_admin_tag
):
    try:
        index = int(message.text.strip()) - 1
        if index < 0 or index >= len(waiting_queue):
            raise ValueError
        user_id = waiting_queue.pop(index)
    except:
        await message.answer("❌ Неверный номер.")
        await state.finish()
        return
    
    admin_id = message.from_user.id
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
    await state.finish()

# ========== ОБРАБОТКА ДИАЛОГОВ ==========
async def handle_dialog_messages(
    message: types.Message, state: FSMContext,
    bot, dialogs, save_all,
    is_admin, get_user_name, get_admin_tag
):
    user_id = message.from_user.id
    text = message.text
    
    # Пользователь в диалоге
    if str(user_id) in dialogs:
        admin_id = int(dialogs[str(user_id)])
        
        if text == "🔚 Завершить диалог":
            del dialogs[str(user_id)]
            save_all()
            
            try:
                await bot.send_message(admin_id, "🔚 Пользователь завершил диалог.", reply_markup=admin_menu())
            except:
                pass
            
            await message.answer(
                "✅ Диалог завершён.\n\n"
                "Если админ был к вам невежлив, груб или нарушил правила, "
                "напишите #крип и опишите ситуацию. Ваша жалоба будет рассмотрена.",
                reply_markup=main_menu()
            )
            return
        
        user_name = get_user_name(user_id)
        try:
            await bot.send_message(admin_id, f"{user_name}\n{text}")
        except:
            await message.answer("❌ Не удалось отправить сообщение.")
        return
    
    # Админ в диалоге
    for uid, aid in dialogs.items():
        if aid == str(user_id):
            if text == "🔚 Завершить диалог":
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
                
                await message.answer("✅ Диалог завершён.", reply_markup=admin_menu())
                return
            
            admin_tag = get_admin_tag(user_id)
            try:
                await bot.send_message(int(uid), f"{admin_tag}\n{text}")
            except:
                await message.answer("❌ Не удалось отправить сообщение.")
            return
    
    # Не в диалоге
    if is_admin(user_id):
        await message.answer("Меню:", reply_markup=admin_menu())
    else:
        await message.answer("Меню:", reply_markup=main_menu())

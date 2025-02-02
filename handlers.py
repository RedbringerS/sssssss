import logging
from datetime import datetime
from html import escape
import asyncpg
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
import text
from kb import get_menu, get_subscription_button
from states import Gen
from db_config import DB_CONFIG


router = Router()
user_states = {}


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                user_exists = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
                if not user_exists:
                    try:
                        async with conn.transaction():
                            await conn.execute("INSERT INTO users (user_id, last_execution_time) VALUES ($1, $2)",
                                               user_id, datetime.now())
                    except Exception as e:
                        logging.error(f"Ошибка при вставке в таблицу пользователей: {e}")
                        raise
    except Exception as e:
        logging.error(f"Ошибка подключения к PostgreSQL: {e}")
    menu = await get_menu(user_id, is_user_subscribed)

    if menu:
        await state.set_state(Gen.text_prompt)
        await message.answer(
            text.greet.format(name=message.from_user.full_name), reply_markup=menu
        )
    else:
        logging.error("Ошибка при создании меню.")


async def send_info_message_to_subscribers(info_message, bot):
    logging.info("я тут")
    logging.info(info_message)
    for user_id in await is_user_sub():
        try:
            escaped_message = escape(f"Информационное сообщение: {info_message}")
            await bot.send_message(chat_id=user_id, text=escaped_message)

        except Exception as e:
            logging.error(f"Не удалось отправить информационное сообщение пользователю {user_id}: {e}")


async def is_user_sub():
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                result = await conn.fetch("SELECT user_id FROM subscribers")
                return [row['user_id'] for row in result]
    except asyncpg.exceptions.PostgresError as e:
        logging.error(f"Ошибка проверки подписки пользователя: {e}")
        return []


async def is_user_subscribed(user_id):
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1 FROM subscribers WHERE user_id = $1", user_id)
                return bool(result)
    except asyncpg.exceptions.PostgresError as e:
        logging.error(f"Ошибка проверки подписки пользователя: {e}")
        return False


@router.callback_query(F.data == "generate_text")
async def generate_text_handler(clbck: CallbackQuery, state: FSMContext):
    if clbck.data == "generate_text":
        user_id = clbck.from_user.id
        await state.set_state(Gen.text_prompt)
        await clbck.message.edit_text(text.gen_text)
        await subscribe_user(clbck, user_id, state)
        await get_menu(user_id, is_user_subscribed)


async def subscribe_user(clbck: CallbackQuery, user_id, state, subscribed=True):
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                if subscribed:
                    await conn.execute("INSERT INTO subscribers (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
                else:
                    await conn.execute("DELETE FROM subscribers WHERE user_id = $1", user_id)
                await state.update_data(subscription_status=subscribed)
                subscription_button = await get_subscription_button(user_id, is_user_subscribed)
                await clbck.bot.edit_message_reply_markup(chat_id=user_id, message_id=clbck.message.message_id,
                                                          reply_markup=InlineKeyboardMarkup(
                                                              inline_keyboard=[[subscription_button]]))
    except Exception as e:
        logging.error(f"Ошибка при управлении подпиской пользователя: {e}")


async def unsubscribe_user(user_id, state):
    try:
        async with asyncpg.create_pool(**DB_CONFIG) as pool:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM subscribers WHERE user_id = $1", user_id)
                await state.update_data(subscription_status=False)
                return True
    except Exception as e:
        logging.error(f"Ошибка управления подпиской пользователя: {e}")
        return False


@router.callback_query(F.data == "subscribe")
async def subscribe_handler(clbck: CallbackQuery, state: FSMContext):
    user_id = clbck.from_user.id
    last_execution_time = await subscribe_user(clbck, user_id, state, subscribed=True)
    if last_execution_time:
        await state.set_state(Gen.text_prompt)
        await clbck.message.answer("Вы успешно подписались на рассылку!")
        subscription_button = await get_subscription_button(user_id, is_user_subscribed)
        await clbck.bot.edit_message_reply_markup(chat_id=user_id, message_id=clbck.message.message_id,
                                                  reply_markup=InlineKeyboardMarkup(
                                                      inline_keyboard=[[subscription_button]]))
    else:
        await clbck.message.answer("Произошла ошибка при подписке. Попробуйте позже.")


@router.callback_query(F.data == "unsubscribe")
async def unsubscribe_handler(clbck: CallbackQuery, state):
    user_id = clbck.from_user.id
    unsubscribed = await unsubscribe_user(user_id, state)
    if unsubscribed:
        await clbck.message.answer("Вы успешно отписались от рассылки.")
        await edit_menu(clbck, user_id, is_user_subscribed)
    else:
        await clbck.message.answer("Произошла ошибка при отписке. Попробуйте позже.")


async def edit_menu(clbck: CallbackQuery, user_id, is_user_subscribed_func):
    try:
        subscription_button = await get_subscription_button(user_id, is_user_subscribed_func)
        await clbck.bot.edit_message_reply_markup(chat_id=clbck.from_user.id, message_id=clbck.message.message_id,
                                                  reply_markup=InlineKeyboardMarkup(
                                                      inline_keyboard=[[subscription_button]]))
        logging.info(f"Меню успешно обновлено для пользователя {user_id}.")
    except Exception as e:
        logging.error(f"Ошибка обновления меню для пользователя {user_id}: {e}")

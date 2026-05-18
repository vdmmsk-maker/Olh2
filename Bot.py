import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

TOKEN = os.environ.get("BOT_TOKEN", "8724325796:AAFjf-nE5nUbj_Oe_f7m10uPHH0K9dWUPAA")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "196229419"))

CHOOSE_TYPE, ENTER_FLAT, ENTER_NAME, ENTER_PHONE, ENTER_TICKET, ENTER_MESSAGE = range(6)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["📋 Обращение"], ["💡 Предложение"], ["⚠️ Жалоба"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\nЭто бот для связи жителей с Управляющей компанией.\n\nВыберите тип обращения:",
        reply_markup=reply_markup,
    )
    return CHOOSE_TYPE


async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text not in ["📋 Обращение", "💡 Предложение", "⚠️ Жалоба"]:
        await update.message.reply_text("Пожалуйста, выберите пункт из меню.")
        return CHOOSE_TYPE
    context.user_data["type"] = text
    await update.message.reply_text(
        f"Вы выбрали: {text}\n\n🏠 Введите номер вашей квартиры:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_FLAT


async def enter_flat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flat = update.message.text.strip()
    if not flat.isdigit():
        await update.message.reply_text("Пожалуйста, введите номер квартиры цифрами:")
        return ENTER_FLAT
    context.user_data["flat"] = flat
    await update.message.reply_text("👤 Введите ваше ФИО:")
    return ENTER_NAME


async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("Пожалуйста, введите полное ФИО:")
        return ENTER_NAME
    context.user_data["name"] = name
    contact_button = KeyboardButton("📱 Отправить мой номер", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "📞 Введите ваш номер телефона\n\nНапример: +79001234567\n\nИли нажмите кнопку ниже:",
        reply_markup=keyboard,
    )
    return ENTER_PHONE


async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    else:
        phone = update.message.text.strip()
        digits = phone.replace("+","").replace("-","").replace(" ","").replace("(","").replace(")","")
        if not digits.isdigit() or len(digits) < 10:
            await update.message.reply_text("⚠️ Введите корректный номер телефона.\nНапример: +79001234567")
            return ENTER_PHONE
    context.user_data["phone"] = phone
    keyboard = ReplyKeyboardMarkup([["➡️ Пропустить"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "🔖 Если оставляли заявку в другом сервисе (ГИС ЖКХ, Госуслуги) — введите её номер.\n\nЕсли нет — нажмите Пропустить:",
        reply_markup=keyboard,
    )
    return ENTER_TICKET


async def enter_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["ticket"] = None if text == "➡️ Пропустить" else text
    appeal_type = context.user_data["type"]
    await update.message.reply_text(
        f"✍️ Напишите текст вашего обращения ({appeal_type.split()[-1].lower()}):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ENTER_MESSAGE


async def enter_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip()
    user_data = context.user_data
    appeal_type = user_data.get("type", "Обращение")
    flat = user_data.get("flat", "—")
    name = user_data.get("name", "—")
    phone = user_data.get("phone", "—")
    ticket = user_data.get("ticket")
    username = update.message.from_user.username or "нет username"
    user_id = update.message.from_user.id
    ticket_line = f"Номер заявки: {ticket}\n" if ticket else "Номер заявки: не указан\n"
    admin_message = (
        f"📬 НОВОЕ ОБРАЩЕНИЕ\n"
        f"{'─' * 30}\n"
        f"Тип: {appeal_type}\n"
        f"Квартира: №{flat}\n"
        f"ФИО: {name}\n"
        f"Телефон: {phone}\n"
        f"{ticket_line}"
        f"Telegram: @{username} (ID: {user_id})\n"
        f"{'─' * 30}\n"
        f"Текст:\n{message_text}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    ticket_confirm = f"Номер заявки: {ticket}\n" if ticket else ""
    keyboard = [["📋 Обращение"], ["💡 Предложение"], ["⚠️ Жалоба"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        f"✅ Ваше обращение принято!\n\nТип: {appeal_type}\nКвартира: №{flat}\nФИО: {name}\nТелефон: {phone}\n{ticket_confirm}\nУК рассмотрит обращение в ближайшее время.\n\nХотите отправить ещё одно?",
        reply_markup=reply_markup,
    )
    context.user_data.clear()
    return CHOOSE_TYPE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог отменён. Напишите /start чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END


def main():
    app = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            ENTER_FLAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_flat)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            ENTER_PHONE: [
                MessageHandler(filters.CONTACT, enter_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone),
            ],
            ENTER_TICKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_ticket)],
            ENTER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    print("✅ Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()

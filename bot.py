import logging
import os
from datetime import date
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton as IB
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN o'rnatilmagan!")

ADMIN_IDS = [327097376, 848972474, 5601591079]

def arrival_kb():
    return InlineKeyboardMarkup([
        [IB("5 minutda", callback_data='time_5'), IB("10 minutda", callback_data='time_10')],
        [IB("15 minutda", callback_data='time_15'), IB("20 minutda", callback_data='time_20')],
        [IB("Men Keldim!", callback_data='time_now')],
        [IB("⚙️ Sozlamalar", callback_data='settings')]
    ])

def settings_kb():
    return InlineKeyboardMarkup([
        [IB("✏️ Ismlarni o'zgartirish", callback_data='edit_names')],
        [IB("🖼 Rasmni o'zgartirish", callback_data='edit_photo')],
        [IB("❌ Bekor qilish", callback_data='cancel_settings')]
    ])

async def show_menu(target, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    if 'parent_full' not in data or 'child_full' not in data:
        return False

    parent = data['parent_full']
    child = data['child_full']
    photo_note = "\n(Rasm yo‘q — keyinroq “⚙️ Sozlamalar” orqali qo‘shishingiz mumkin)" if not data.get('child_photo_id') else ""

    text = f"Assalomu alaykum, {parent}! 👋\nFarzandingiz: {child}{photo_note}\n\nQachon yetib kelasiz?"

    if hasattr(target, 'message'):
        await target.message.reply_text(text, reply_markup=arrival_kb())
    else:
        await target.edit_message_text(text, reply_markup=arrival_kb())
    return True

async def notify_all_admins(context: ContextTypes.DEFAULT_TYPE, title: str, time_text: str):
    data = context.user_data
    parent = data.get('parent_full', 'Nomaʼlum')
    child = data.get('child_full', 'Nomaʼlum')

    msg = f"{title}\n\n👨‍👩‍👧 Ota-ona: {parent}\n👦 Farzand: {child}\n🕐 Kelish vaqti: {time_text}"

    photo_id = data.get('child_photo_id')

    for admin_id in ADMIN_IDS:
        try:
            if photo_id:
                await context.bot.send_photo(admin_id, photo_id, caption=msg)
            else:
                await context.bot.send_message(admin_id, msg)
        except Exception as e:
            logging.error(f"Adminga yuborishda xato (ID: {admin_id}): {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await show_menu(update, context):
        return
    await update.message.reply_text("Assalomu alaykum! 😊\nIltimos, ota-onaning to‘liq ismini yozing (masalan: Ahmedov Ali):")
    context.user_data['waiting_for'] = 'parent'

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    if 'parent_full' in data and 'child_full' in data:
        await show_menu(update, context)
        return

    waiting = data.get('waiting_for')
    if waiting == 'parent':
        data['parent_full'] = update.message.text.strip()
        await update.message.reply_text("Rahmat! Endi farzandingizning to‘liq ismini yozing (masalan: Aliyeva Barno):")
        data['waiting_for'] = 'child'
    elif waiting == 'child':
        data['child_full'] = update.message.text.strip()
        await update.message.reply_text(
            "Rahmat! Endi ixtiyoriy ravishda farzandingizning rasmini yuborishingiz mumkin.\n"
            "Bu bizga bolani tezroq tayyorlab berishga yordam beradi 😊\n\n"
            "Rasmini yuboring yoki o‘tkazib yuborish:",
            reply_markup=InlineKeyboardMarkup([[IB("O‘tkazib yuborish", callback_data='skip_photo')]])
        )
        data['waiting_for'] = 'child_photo'

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for') in ['child_photo', 'edit_photo']:
        context.user_data['child_photo_id'] = update.message.photo[-1].file_id
        await update.message.reply_text("✅ Rasm muvaffaqiyatli saqlandi!")
        await show_menu(update, context)
        context.user_data['waiting_for'] = None

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_data = context.user_data

    if data == 'skip_photo':
        await query.edit_message_text(
            "✅ Ro‘yxatdan o‘tdingiz!\n"
            "Rasmni keyinroq “⚙️ Sozlamalar” orqali qo'shishingiz mumkin.\n\n"
            "Qachon kelasiz?",
            reply_markup=arrival_kb()
        )
        user_data['waiting_for'] = None

    elif data == 'settings':
        await query.edit_message_text("⚙️ Sozlamalar\n\nNima qilmoqchisiz?", reply_markup=settings_kb())

    elif data == 'cancel_settings':
        await show_menu(query, context)

    elif data == 'edit_names':
        user_data.clear()
        await query.edit_message_text("Ismlarni o‘zgartiramiz! 📝\n\nYangi ota-ona ismini yozing:")
        user_data['waiting_for'] = 'parent'

    elif data == 'edit_photo':
        await query.edit_message_text("Yangi rasmni yuboring:")
        user_data['waiting_for'] = 'edit_photo'

    elif data.startswith('time_'):
        times = {
            'time_5': '5 daqiqada',
            'time_10': '10 daqiqada',
            'time_15': '15 daqiqada',
            'time_20': '20 daqiqada',
            'time_now': 'Hoziroq (Men keldim!)'
        }
        display_time = times[data]

        if data == 'time_now':
            today = str(date.today())
            count = user_data.get('arrived_today_count', 0)
            last_date = user_data.get('last_arrived_date', None)

            if last_date != today:
                count = 1
                user_data['last_arrived_date'] = today
            else:
                count += 1
            user_data['arrived_today_count'] = count

            if count == 1:
                await notify_all_admins(context, "🚨 OTA-ONA KELDI!", "Hozir")
                response = "✅ Rahmat! Bizga xabaringiz yetib keldi:\nHoziroq sizni farzandingizni olib chiqamiz."
            else:
                await notify_all_admins(context, "😠 OTA-ONA KUTIB QOLDI!", "Hoziroq")
                response = "Kelganingizni navbatchiga qayta yubordik, kuttirib qo‘yganimiz uchun uzr!"
        else:
            await notify_all_admins(context, "🚨 YANGI KELUVCHI!", display_time)
            response = f"✅ Rahmat! Bizga xabar yetib bordi:\n{display_time} sizni farzandingizni tayyorlab turamiz."

        await query.edit_message_text(response, reply_markup=arrival_kb())

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Bot ishga tushdi! 3 ta admin ga bildirishnoma yuboriladi ✅")
    app.run_polling()

if __name__ == '__main__':
    main()

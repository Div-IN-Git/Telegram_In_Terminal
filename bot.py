import os
from dotenv import load_dotenv
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN = "8458001052:AAGwkvpa15VLfXv69vkAnS3HjcAR-8S8p8U"

# Simple in-memory storage (later we make JSON-based index)
file_store = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("BITS Manager online. Use /force to upload, /give <name> to download.")

# /force command (expects a file upload)
async def force_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me the file(s) you want to store. I’ll handle the rest.")

# Handle file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc: Document = update.message.document
    file_name = doc.file_name

    # Delete old version if exists
    if file_name in file_store:
        old_message_id = file_store[file_name]
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=old_message_id)
        except:
            pass

    # Save new file reference
    sent_message = await doc.get_file()
    file_store[file_name] = update.message.message_id

    await update.message.reply_text(f"Stored: {file_name} (latest version)")

# /give command
async def give_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /give filename.ext")
        return

    requested = context.args[0]
    if requested in file_store:
        message_id = file_store[requested]
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=update.effective_chat.id,
            message_id=message_id
        )
    else:
        await update.message.reply_text(f"No file named {requested} found.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("force", force_command))
    app.add_handler(CommandHandler("give", give_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()


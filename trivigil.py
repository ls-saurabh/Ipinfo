import os
import logging
import subprocess
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import asyncio

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID'))

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Dictionary to store subprocess references and status for each user
user_processes = {}
awaiting_response = {}  # Track if a user is awaiting a response for a prompt

def is_authorized(update: Update) -> bool:
    """Check if the user is authorized."""
    return update.effective_user.id == AUTHORIZED_USER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays buttons for SQLmap and Nikto on the /start command."""
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized access!")
        return

    # Inline buttons for SQLmap and Nikto
    keyboard = [
        [InlineKeyboardButton("SQLmap", callback_data="sqlmap")],
        [InlineKeyboardButton("Nikto", callback_data="nikto")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a tool to run:", reply_markup=reply_markup)

async def tool_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles tool selection and asks for the URL."""
    query = update.callback_query
    await query.answer()
    tool = query.data  # "sqlmap" or "nikto"
    context.user_data["selected_tool"] = tool
    await query.edit_message_text(f"Please provide the URL for {tool.capitalize()} analysis:")

async def handle_url_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles URL input, constructs the command, and executes it with interactive prompts."""
    if not is_authorized(update):
        await update.message.reply_text("Unauthorized access!")
        return

    tool = context.user_data.get("selected_tool")
    if not tool:
        await update.message.reply_text("Error: No tool selected. Please use /start to select a tool.")
        return

    url = update.message.text.strip()
    command = ""
    if tool == "sqlmap":
        command = (
            f'cd /data/data/com.termux/files/home/sqlmap && '
            f'python3 sqlmap.py -u {url} --dbs --user-agent="Mozilla/5.0" --tamper=space2comment --tables'
        )
    elif tool == "nikto":
        command = (
            f'cd /data/data/com.termux/files/home/nikto/program && '
            f'./nikto.pl -h {url} -useragent "Mozilla/5.0"'
        )

    # Inline button to stop the command
    stop_keyboard = [[InlineKeyboardButton("Stop", callback_data="stop_command")]]
    stop_markup = InlineKeyboardMarkup(stop_keyboard)
    await update.message.reply_text("Executing command...", reply_markup=stop_markup)

    # Run the command asynchronously
    process = await asyncio.create_subprocess_shell(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
    )
    user_processes[update.effective_user.id] = process
    awaiting_response[update.effective_user.id] = False  # Track if waiting for response

    # Read the output interactively
    while True:
        output = await process.stdout.readline()
        if output == b"" and process.poll() is not None:
            break

        decoded_output = output.decode("utf-8").strip()
        
        # Check for prompts and ask the user to respond if found
        if "[Y/n/q]" in decoded_output or "[Y/N]" in decoded_output:
            awaiting_response[update.effective_user.id] = True
            await update.message.reply_text("The command requires a Y/N response. Please reply with 'Y' or 'N'.")
            return  # Wait for the user's next message to provide the response

        elif decoded_output and not awaiting_response[update.effective_user.id]:
            # Only send non-empty messages if not awaiting a response
            await update.message.reply_text(decoded_output[:4000])

    # Handle process completion and cleanup
    stdout, stderr = await process.communicate()
    del user_processes[update.effective_user.id]
    awaiting_response.pop(update.effective_user.id, None)
    if stdout:
        await update.message.reply_text(f"{tool.capitalize()} Output:\n{stdout.decode()[:4000]}")
    if stderr:
        await update.message.reply_text(f"{tool.capitalize()} Error:\n{stderr.decode()[:4000]}")

async def handle_user_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles Y/N responses from the user when prompted by the bot."""
    user_id = update.effective_user.id

    # Only handle response if awaiting one
    if awaiting_response.get(user_id, False):
        response = update.message.text.strip().lower()
        if response in ["y", "n"]:
            process = user_processes.get(user_id)
            if process:
                await process.stdin.write(f"{response.upper()}\n".encode("utf-8"))
                await process.stdin.drain()
            awaiting_response[user_id] = False
        else:
            await update.message.reply_text("Invalid input. Please reply with 'Y' or 'N'.")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stops the running command when the user clicks 'Stop'."""
    query = update.callback_query
    await query.answer()

    # Get the user's process and terminate it if exists
    process = user_processes.get(update.effective_user.id)
    if process:
        try:
            process.terminate()
            await query.edit_message_text("Command stopped by the user.")
            del user_processes[update.effective_user.id]
            awaiting_response.pop(update.effective_user.id, None)
        except ProcessLookupError:
            await query.edit_message_text("The command has already finished.")
    else:
        await query.edit_message_text("No running command to stop.")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(tool_selected, pattern="^(sqlmap|nikto)$"))
    application.add_handler(CallbackQueryHandler(stop_command, pattern="^stop_command$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_response))

    application.run_polling()

if __name__ == '__main__':
    main()
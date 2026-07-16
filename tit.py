# tit.py
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import *
from telethon.errors import RPCError

# ====== CONFIG ======
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHAT_ID = int(os.getenv("CHAT_ID"))
SESSION_NAME = os.getenv("SESSION_NAME", "div")
DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

if not API_ID or not API_HASH or not CHAT_ID:
    print("Missing API_ID, API_HASH or CHAT_ID in .env")
    sys.exit(1)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ====== commands ======
async def force_file(filename: str):
    if not os.path.exists(filename):
        print(f"Error: file '{filename}' does not exist")
        return

    try:
        # Tell the group/bot we are forcing this file
        await client.send_message(CHAT_ID, f"/force {filename}")
        # Upload the actual file as you (so bot will see it as YOUR upload)
        await client.send_file(CHAT_ID, filename)
        print(f"Uploaded and forced '{filename}' to group {CHAT_ID}")
    except RPCError as e:
        print("Telegram RPC error:", e)


async def give_telegram(filename: str):
    try:
        # Ask the bot in the group to give the file (it will post to the group)
        await client.send_message(CHAT_ID, f"/give {filename}")
        print(f"Requested '{filename}' from bot in group. Check Telegram.")
    except RPCError as e:
        print("Telegram RPC error:", e)


async def give_local(filename: str):
    """
    Search the group's messages (newest first) for a document with the given
    filename and download the **latest** occurrence into local Downloads.
    """
    print(f"Searching group {CHAT_ID} for latest '{filename}'...")
    found = False
    # iter_messages yields newest first by default
    async for msg in client.iter_messages(CHAT_ID, limit=None):
        if msg.file and getattr(msg.file, "name", None) == filename:
            # construct destination path
            dest = os.path.join(DOWNLOAD_DIR, filename)
            try:
                await msg.download_media(file=dest)
                print(f"Downloaded latest '{filename}' to: {dest}")
                found = True
            except Exception as e:
                print(f"Error downloading file: {e}")
            break

    if not found:
        print(f"No file named '{filename}' found in group {CHAT_ID}.")


async def main():
    if len(sys.argv) < 3:
        print("Usage: python tit.py /force <filename>  OR  /give <filename>  OR  /gvl <filename>")
        return

    command = sys.argv[1]
    filename = " ".join(sys.argv[2:])  # support spaces in filename

    if command == "/force":
        await force_file(filename)
    elif command == "/give":
        await give_telegram(filename)
    elif command == "/gvl":
        await give_local(filename)
    else:
        print("Invalid command. Use /force, /give or /gvl")


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())

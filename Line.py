import logging
import asyncio
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from cachetools import TTLCache

# Configuration
API_ID = '1747534'
API_HASH = '5a2684512006853f2e48aca9652d83ea'
SESSION_STRING = '1BVtsOGgBu2LspEEeVvgzMKpcl4eA1X-F5mPytbGAAzGj2MeduTtSM5QUhx3eSKfRjhxqVXr47NsUj1EYYRH5zZyxQ2yvUqTdHtFzNM1lniJGPhIhmRUn21C3hPjYXdEXJz5oOXC9wvwvUGNj3Moo-atcP0HuMiwydv0PVZ59RWdkHrXQeqHSXKnzbcw_9LrmhdjFf-6KwT3Hfd2LAxcIZ2hmOoRb9oqpNniGU6wQ1KRyMaCfM2bT5XWfUDGq9MG-iC2NXGaC6kev_riTQwvoveioRelU7HP4QV3wC0aPayWpaargbhPtEdl8Y2Vnhln88lBbZj1gJj7UjxqxyzJXfwii6PYHFsg='
#SESSION_STRING = '1BJWap1sBu1raOBOsqXCyc7eoNH85-22KicromTC0zEcF6RI4LAiORqIiPhIhelzUByf7ZXMTRsSLOPCJlS4yVkYu7QiA59HOHI5E6OVAUT7Hlz3Z7IdFBIA_7WVwRdqTDLLCJrmtYwJFUR_ohMyFLcsGPfoK6RtzbWR9dgrG_UVrPNmo0SHPSoJ-v2Ad7PfC8hjxYh9Q915fCnqVIg2dOjQyrPSbpgCprd97_Krn1l-l-ayCv8BD7MJKlpLe1doP5eclkCWMQMjKpf06HwFbBCjn4f6YRFpp436ZkhBMM8amR8xudueevRyWZ5p8YjmaGQfA-ZKB0D9HcONCPFhYPtjL5hSnOy8='

# Initialize the userbot
user_bot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Setup logging (set to WARNING for optimized production logging)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Chat IDs
#SOURCE_CHAT_ID = -1002081479520  # Source channel ID
SOURCE_CHAT_ID = -1001262096355  # Source channel ID
TARGET_CHAT_ID = -1001075055733 # Express Line
#TARGET_CHAT_ID = -1002497511035   # Destination channel ID

# Mapping between source and destination message IDs using TTLCache (expires after 24 hours)
message_map = TTLCache(maxsize=10000, ttl=86400)

# === Regex Filtering Setup ===
# Regex to match URLs (http/https or www links)
#URL_REGEX = re.compile(r'(https?://\S+|www\.\S+)', re.IGNORECASE)
URL_REGEX = re.compile(
    r'(https?://[^\s]+|'              # Matches http:// or https:// URLs
    r'www\.[^\s]+|'                   # Matches URLs starting with www. (dot required)
    r't\.me/[^\s]+|'                  # Matches Telegram short links t.me/...
    r'telegram\.me/[^\s]+|'           # Matches Telegram links telegram.me/...
    r'[^\s]+\.[a-z]{2,}(?=\s|$|[^\w]))',  # Matches bare domains (any TLD of at least 2 letters)
    re.IGNORECASE
)

# Regex to match Telegram usernames (starting with '@')
USERNAME_REGEX = re.compile(r'@\w+', re.IGNORECASE)

# Regex to match common emoji ranges
EMOJI_REGEX = re.compile(
    r'['
    u"\U0001F600-\U0001F64F"  # Emoticons
    u"\U0001F446-\U0001F44F"  # Common hand emojis
    ']',
    flags=re.UNICODE
)

# New: Regex for forbidden words (e.g., "ID", "Bet") as whole words
FORBIDDEN_WORDS_REGEX = re.compile(r'\b(?:ID|Bet)\b', re.IGNORECASE)

def contains_forbidden(text: str) -> bool:
    """
    Returns True if the text contains any forbidden content:
    - URLs or website links
    - Telegram usernames (starting with '@')
    - Any emoji
    """
    if URL_REGEX.search(text):
        return True
    if USERNAME_REGEX.search(text):
        return True
    if EMOJI_REGEX.search(text):
        return True
    if FORBIDDEN_WORDS_REGEX.search(text):
        return True
    return False

async def forward_text_message(text, source_id):
    """
    Helper function to forward a text message to the target channel
    and update the message mapping.
    """
    try:
        dest_message = await user_bot.send_message(TARGET_CHAT_ID, text)
        message_map[source_id] = dest_message.id
        logger.info(f"Forwarded message {source_id} as {dest_message.id}.")
        return dest_message.id
    except FloodWaitError as e:
        logger.warning(f"Rate limited. Retrying in {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
        return await forward_text_message(text, source_id)
    except Exception as e:
        logger.error(f"Error forwarding message {source_id}: {e}", exc_info=True)
        return None

@user_bot.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def new_message_handler(event):
    if event.message.text:
        if contains_forbidden(event.message.text):
            logger.info(f"Message (ID: {event.message.id}) contains forbidden content; ignoring.")
            return
        logger.info(f"Received new message (ID: {event.message.id}) with acceptable content.")
        asyncio.create_task(forward_text_message(event.message.text, event.message.id))
    else:
        logger.info("Message has no text; ignoring.")


#@user_bot.on(events.NewMessage(chats=SOURCE_CHAT_ID))
#async def new_message_handler(event):
#    if event.message.text:
#        logger.info(f"Received new message (ID: {event.message.id}).")
#        #await forward_text_message(event.message.text, event.message.id)
#        asyncio.create_task(forward_text_message(event.message.text, event.message.id))
#    else:
#        logger.info("Message has no text; ignoring.")

@user_bot.on(events.MessageEdited(chats=SOURCE_CHAT_ID))
async def message_edited_handler(event):
    if event.message.text:
        source_id = event.message.id
        logger.info(f"Edited message received (Source ID: {source_id}).")
        if source_id in message_map:
            dest_id = message_map[source_id]
            try:
                await user_bot.edit_message(TARGET_CHAT_ID, dest_id, event.message.text)
                logger.info(f"Edited destination message {dest_id} for source message {source_id}.")
            except Exception as e:
                logger.error(f"Error editing message {source_id}: {e}", exc_info=True)
        else:
            await forward_text_message(event.message.text, source_id)
    else:
        logger.info("Edited message has no text; ignoring.")

@user_bot.on(events.MessageDeleted(chats=SOURCE_CHAT_ID))
async def message_deleted_handler(event):
    logger.info(f"Message(s) deleted in source channel: {event.deleted_ids}")
    for source_id in event.deleted_ids:
        if source_id in message_map:
            dest_id = message_map.pop(source_id)
            try:
                await user_bot.delete_messages(TARGET_CHAT_ID, dest_id)
                logger.info(f"Deleted destination message {dest_id} for source message {source_id}.")
            except Exception as e:
                logger.error(f"Error deleting message {source_id}: {e}", exc_info=True)
        else:
            logger.info(f"No mapping for deleted source message {source_id}.")

async def start_userbot():
    try:
        await user_bot.start()
        logger.info("Bot is Online")
        #print("Bot is Online")
        await user_bot.run_until_disconnected()
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(start_userbot())

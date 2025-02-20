import logging
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from cachetools import TTLCache

# Configuration
API_ID = '1747534'
API_HASH = '5a2684512006853f2e48aca9652d83ea'
SESSION_STRING = '1BVtsOGgBu2LspEEeVvgzMKpcl4eA1X-F5mPytbGAAzGj2MeduTtSM5QUhx3eSKfRjhxqVXr47NsUj1EYYRH5zZyxQ2yvUqTdHtFzNM1lniJGPhIhmRUn21C3hPjYXdEXJz5oOXC9wvwvUGNj3Moo-atcP0HuMiwydv0PVZ59RWdkHrXQeqHSXKnzbcw_9LrmhdjFf-6KwT3Hfd2LAxcIZ2hmOoRb9oqpNniGU6wQ1KRyMaCfM2bT5XWfUDGq9MG-iC2NXGaC6kev_riTQwvoveioRelU7HP4QV3wC0aPayWpaargbhPtEdl8Y2Vnhln88lBbZj1gJj7UjxqxyzJXfwii6PYHFsg='

# Initialize the userbot
user_bot = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Setup logging (set to WARNING for optimized production logging)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Chat IDs
SOURCE_CHAT_ID = -1002081479520  # Source channel ID
TARGET_CHAT_ID = -1002497511035   # Destination channel ID

# Mapping between source and destination message IDs using TTLCache (expires after 24 hours)
message_map = TTLCache(maxsize=10000, ttl=86400)

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
        logger.info(f"Received new message (ID: {event.message.id}).")
        await forward_text_message(event.message.text, event.message.id)
    else:
        logger.info("Message has no text; ignoring.")

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
        print("Bot is Online")
        await user_bot.run_until_disconnected()
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(start_userbot())

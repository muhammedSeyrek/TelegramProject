import os
import json
import logging
import re
import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel, MessageMediaDocument

# Logging configuration
logging.basicConfig(level=logging.INFO, filename='telegram_bot.log', 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Load API credentials securely
def loadConfig():
    try:
        with open('config.json') as configFile:
            config = json.load(configFile)
        return config['apiId'], config['apiHash'], config['phoneNumber']
    except Exception as e:
        logging.error(f"Error loading configuration file: {e}")
        return None, None, None

# Get channel details
async def getChannelDetails(client, channel):
    try:
        fullChat = await client.get_entity(channel.id)
        about = getattr(fullChat, 'about', 'No description available.')
        return about
    except Exception as e:
        logging.error(f'Error getting channel description: {e}')
        return None

# Download specific files (like .rar, .zip, .txt) from a message
async def downloadFile(client, message, downloadPath):
    try:
        if message.media and isinstance(message.media, MessageMediaDocument):
            # Check file extension to only download specific file types
            fileName = message.file.name
            if fileName and fileName.lower().endswith(('.rar', '.zip', '.txt')):
                filePath = await client.download_media(message, downloadPath)
                logging.info(f'File downloaded to: {filePath}')
                print(f'File downloaded to: {filePath}')
                return filePath
        return None
    except Exception as e:
        logging.error(f'Error downloading file: {e}')
        return None

# Process messages to only download specified file types
async def processMessages(client, channel, messageLimit, downloadPath):
    try:
        messages = await client.get_messages(channel, messageLimit)
        randomMessages = []
        otherLinks = set()
        joinLinks = set()
        fileCount = 0
        downloadTasks = []  # List to hold download tasks
        
        for message in messages:
            if message.text:
                randomMessages.append(message.text)
                # Limit to 5 random messages for brevity
                if len(randomMessages) > 5:
                    randomMessages.pop(0)

                urls = re.findall(r'http[s]?://\S+', message.text)  # URL detection
                joinLinks.update(re.findall(r'(https?://t\.me/joinchat/\S+|https?://t\.me/\+\S+)', message.text))  # Join link detection
                otherLinks.update(urls)

            # Check and schedule specific file downloads
            if isinstance(message.media, MessageMediaDocument):
                fileName = message.file.name
                if fileName and fileName.lower().endswith(('.rar', '.zip', '.txt')):
                    fileCount += 1
                    downloadTask = downloadFile(client, message, downloadPath)
                    downloadTasks.append(downloadTask)  # Add download task to the list

        # Run all download tasks concurrently
        await asyncio.gather(*downloadTasks)

        return randomMessages, list(otherLinks), list(joinLinks), fileCount
    except Exception as e:
        logging.error(f'Error processing messages: {e}')
        return [], [], [], 0

# Main function
async def main():
    apiId, apiHash, phoneNumber = loadConfig()
    if not all([apiId, apiHash, phoneNumber]):
        logging.error("Missing API credentials.")
        return
    
    client = TelegramClient('session_name', apiId, apiHash)
    try:
        await client.start(phoneNumber)
        logging.info("Successfully connected to Telegram!")
    except Exception as e:
        logging.error(f"Error logging into Telegram: {e}")
        return

    messageLimit = input("Enter the number of recent messages to read: ").strip()
    downloadPath = "downloads/"  # Dosyaların indirileceği dizin

    # İndirilecek dosyaların dizinini oluştur
    if not os.path.exists(downloadPath):
        os.makedirs(downloadPath)

    results = []

    try:
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, Channel):
                channel = dialog.entity
                logging.info(f'Channel Name: {channel.title}, Channel ID: {channel.id}')
                
                about = await getChannelDetails(client, channel)
                randomMessages, otherLinks, joinLinks, fileCount = await processMessages(client, channel, int(messageLimit), downloadPath)
                
                # Creating JSON object
                channelInfo = {
                    "telegram_channel": f"t.me/{channel.username}",
                    "scan": True,
                    "detail": {
                        "name": channel.title,
                        "link": f"t.me/{channel.username}",
                        "other_telegram_links": joinLinks,
                        "other_links": [link for link in otherLinks if 't.me' not in link],
                        "file_count": fileCount,  # Toplam dosya sayısı
                        "random_messages": randomMessages[:5],  # Limiting to 5 random messages
                        "tags": [],  # Placeholder for tags
                    }
                }
                results.append(channelInfo)

        # Output the JSON result
        print(json.dumps(results, indent=4))
    except Exception as e:
        logging.error(f"Error listing channels: {e}")

# Run the Telegram client
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

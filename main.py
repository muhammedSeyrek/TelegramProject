import os
import json
import logging
import re
import asyncio
import random
from telethon import TelegramClient
from telethon.tl.types import Channel, MessageMediaDocument
from telethon.tl.types import MessageMediaPhoto  # For photo detection

data = []

# Logging configuration
logging.basicConfig(level=logging.INFO, filename='telegramBot.log', 
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
        '''
            downloadFile: Downloads specific file types (e.g., .rar, .zip, .txt) from a message.
            message.media: Checks if the message contains media.
            isinstance(message.media, MessageMediaDocument): Confirms the media is a document.
            await client.download_media: Downloads the file to the specified directory.
            try-except: Logs error messages if an exception occurs.
        '''
        if message.media and isinstance(message.media, MessageMediaDocument):
            # Check file extension to only download specific file types
            fileName = message.file.name
            #data.append(fileName.lower().endswith())
            if fileName and fileName.lower().endswith(('.rar', '.zip', '.txt')):
                filePath = await client.download_media(message, downloadPath)
                logging.info(f'File downloaded to: {filePath}')
                print(f'File downloaded to: {filePath}')
                return filePath
        return None
    except Exception as e:
        logging.error(f'Error downloading file: {e}')
        return None
    

# Load timestamp history
def loadTimestampHistory():
    if os.path.exists('timestamp_history.json'):
        with open('timestamp_history.json', 'r') as file:
            return json.load(file)
    return {}

# Save timestamp history
def saveTimestampHistory(timestamp_history):
    with open('timestamp_history.json', 'w') as file:
        json.dump(timestamp_history, file, indent=4)


# Check if a message is new
def isNewMessage(channel_id, message_timestamp, timestamp_history):
    if channel_id in timestamp_history:
        last_timestamp = timestamp_history[channel_id]
        return message_timestamp > last_timestamp
    return True





def filter_urls_from_messages(messages):
    filtered_messages = []
    other_links = set()
    other_telegram_links = set()

    url_pattern = r'http[s]?://\S+'  # Regex to detect general URLs
    telegram_join_pattern = r'https?://t\.me/\S+'  # Regex to extract Telegram links

    for message in messages:
        urls = re.findall(url_pattern, message)  # Extract all URLs from the message
        if urls:
            telegram_links = re.findall(telegram_join_pattern, message)
            # Add Telegram links to other_telegram_links
            other_telegram_links.update(telegram_links)
            # Add remaining links to otherLinks (non-Telegram)
            other_links.update([url for url in urls if url not in telegram_links])
        else:
            # If no URL in the message, add as plain text message
            filtered_messages.append(message)

    return filtered_messages, list(other_links), list(other_telegram_links)


async def processMessages(client, channel, messageLimit, downloadPath, timestamp_history):
    try:
        messages = await client.get_messages(channel, messageLimit)
        randomMessages = []
        otherLinks = set()
        joinLinks = set()
        fileCount = 0
        photoCount = 0
        videoCount = 0
        downloadTasks = []  # List to hold download tasks
        latest_timestamp = None

        if len(messages) > 5:
            randomMessages = random.sample(messages, 5)
        else:
            randomMessages = messages

        channel_id = str(channel.id)  # Get channel ID

        # Use only the text content of messages
        random_text_messages = [msg.text for msg in randomMessages if msg.text]
        
        # Filter URLs and messages
        filtered_messages, new_other_links, new_other_telegram_links = filter_urls_from_messages(random_text_messages)

        # Merge with existing URL sets
        otherLinks.update(new_other_links)
        joinLinks.update(new_other_telegram_links)

        # Check media while processing messages
        for message in messages:
            message_timestamp = message.date.timestamp()  # Get the timestamp of the message
            
            if isNewMessage(channel_id, message_timestamp, timestamp_history):  # Check for new messages
                if latest_timestamp is None or message_timestamp > latest_timestamp:
                    latest_timestamp = message_timestamp  # Update latest timestamp

                # Check photo count
                if isinstance(message.media, MessageMediaPhoto):
                    photoCount += 1

                # Check for videos and files
                elif isinstance(message.media, MessageMediaDocument):
                    fileName = message.file.name
                    # Check if the document is a video
                    if message.document.mime_type.startswith("video"):
                        videoCount += 1
                    # Check file download
                    if fileName and fileName.lower().endswith(('.rar', '.zip', '.txt')):
                        fileCount += 1
                        downloadTask = downloadFile(client, message, downloadPath)
                        downloadTasks.append(downloadTask)

        # Run download tasks
        await asyncio.gather(*downloadTasks)

        # Save the latest timestamp if new messages were processed
        if latest_timestamp:
            timestamp_history[channel_id] = latest_timestamp

        return filtered_messages, list(otherLinks), list(joinLinks), fileCount, photoCount, videoCount
    except Exception as e:
        logging.error(f'Error processing messages: {e}')
        return [], [], [], 0, 0, 0


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
    downloadPath = "Files/"

    # Create the directory for downloaded files
    if not os.path.exists(downloadPath):
        os.makedirs(downloadPath)

    # Load timestamp history
    timestamp_history = loadTimestampHistory()
    results = []

    try:
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, Channel):
                channel = dialog.entity
                logging.info(f'Processing Channel: {channel.title} (ID: {channel.id})')

                # Get channel details and start processing
                about = await getChannelDetails(client, channel)
                randomMessages, otherLinks, joinLinks, fileCount, photoCount, videoCount = await processMessages(client, channel, int(messageLimit), downloadPath, timestamp_history)

                # Ensure results are not empty
                if randomMessages or otherLinks or joinLinks or fileCount or photoCount or videoCount:
                    channelInfo = {
                        "telegramChannel": f"t.me/{channel.username}",
                        "detail": {
                            "name": channel.title,
                            "link": f"t.me/{channel.username}",
                            "otherTelegramLinks": joinLinks,
                            "otherLinks": [link for link in otherLinks if 't.me' not in link],
                            "fileCount": fileCount,
                            "photoCount": photoCount,
                            "videoCount": videoCount,
                            "randomMessages": randomMessages[:5],  # Only text messages
                            "tags": [],  # Placeholder for tags
                        }
                    }
                    results.append(channelInfo)
                else:
                    logging.warning(f"No data collected from {channel.title} (ID: {channel.id})")

        # Save timestamp history
        saveTimestampHistory(timestamp_history)

        # Print results if not empty
        if results:
            print(json.dumps(results, ensure_ascii=False, indent=4))
        else:
            logging.warning("No channels with data to output.")
            print("No data to output.")

    except Exception as e:
        logging.error(f"Error processing channels: {e}")
        print(f"Error: {e}")


# Run the Telegram client

'''
    if __name__ == '__main__':
    This statement checks if the script is run directly.
    If this script is run directly, the code inside this block is executed.
    If it is imported from another script, this block is skipped.
    loop = asyncio.get_event_loop()

    asyncio.get_event_loop() function gets the current asynchronous event loop.
    The event loop is where asynchronous tasks (e.g., functions called with await) are managed and executed.
    This ensures that the asynchronous function (e.g., main) is executed until completion.
    main() is an asynchronous function, so the event loop needs to be active for it to run.
    This line allows the event loop to execute the main function and handle any asynchronous operations.

    loop.run_until_complete(main())
'''

asyncio.run(main())

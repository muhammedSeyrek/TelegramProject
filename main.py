import os, json, logging, re, asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel

# Logging configuration
logging.basicConfig(level = logging.INFO, filename='telegram_bot.log', 
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

# Process messages
async def processMessages(client, channel, limit):
    try:
        messages = await client.get_messages(channel, limit)
        for message in messages:
            if message.sender_id:
                sender = await client.get_entity(message.sender_id)
                senderName = sender.username or sender.first_name or "Unknown"
            else:
                senderName = "Unknown"
            
            if message.text:
                urls = re.findall(r'http[s]?://\S+', message.text)  # URL detection
                joinLinks = re.findall(r'(https?://t\.me/joinchat/\S+|https?://t\.me/\+\S+)', message.text)  # Join link detection
                if joinLinks:
                    logging.info(f'Channel: {channel.title}, Join Links: {joinLinks}')
                    print(f'Channel: {channel.title}, Join Links: {joinLinks}')  # Print to console
                elif urls:
                    logging.info(f'Channel: {channel.title}, Message: {message.text}, URL: {urls}')
                else:
                    logging.info(f'Channel: {channel.title}, Sender: {senderName}, Message: {message.text}')
            else:
                logging.info(f'Channel: {channel.title}, Sender: {senderName}, Message: No text')
    except Exception as e:
        logging.error(f'Error processing messages: {e}')

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

    limit = input("Enter the number of recent messages to read: ").strip()

    try:
        async for dialog in client.iter_dialogs():
            if isinstance(dialog.entity, Channel):
                channel = dialog.entity
                logging.info(f'Channel Name: {channel.title}, Channel ID: {channel.id}')
                
                about = await getChannelDetails(client, channel)
                if about:
                    logging.info(f'Channel Description: {about}')
                
                await processMessages(client, channel, int(limit))
                await asyncio.sleep(1)  # Wait to respect rate limits
    except Exception as e:
        logging.error(f"Error listing channels: {e}")

# Run the Telegram client
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

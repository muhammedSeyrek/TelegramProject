from telethon import TelegramClient, events
from telethon.tl.types import Channel
import re

apiId = input("Enter API ID: ").strip()
apiHash = input("Enter API Hash: ").strip()
phoneNumber = input("Enter telephone number: ").strip()
limit = input("Enter last message limit: ").strip()

# Telegram istemcisini oluştur
client = TelegramClient('session_name', apiId, apiHash)


    
async def main():
    # Telegram'a giriş yap
    await client.start(phoneNumber)
    print("Connect Telegram!")
    
    # List subscribed channels
    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, Channel):
            channel = dialog.entity
            print(f'\n\n\nChannel Name: {channel.title}, Channel ID: {channel.id}')
            
            try:
                # Take details on channel
                full_chat = await client.get_entity(channel.id)
                # Take description on channel
                about = getattr(full_chat, 'about', 'No description available.')
                print(f'Description: {about}')
            except Exception as e:
                print(f'An error occurred while getting the description: {e}')
            
            # Read messages up to the channel's last limit
            messages = await client.get_messages(channel, int(limit))
            for message in messages:
                # Take sender information
                if message.sender_id:
                    sender = await client.get_entity(message.sender_id)
                    sender_name = sender.username or sender.first_name or "Unknown"
                else:
                    sender_name = "Unknown"
                
                # Check URL or Reference
                if message.text:
                    urls = re.findall(r'http[s]?://\S+', message.text)  # Regex using for URL
                    if urls:
                        print(f'Message: {message.text}')
                        print(f'Found URLs: {urls}')
                    else:
                        print(f'Sender: {sender_name}, Time: {message.date}, Message: {message.text}')
                else:
                    print(f'Sender: {sender_name}, Time: {message.date}, Message: No text')


# Run telegram client
with client:
    client.loop.run_until_complete(main())

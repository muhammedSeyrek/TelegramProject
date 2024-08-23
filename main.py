from telethon import TelegramClient, events
from telethon.tl.types import Channel

apiId = input("Enter API ID: ").strip()
apiHash = input("Enter API Hash: ").strip()
phoneNumber = input("Enter telephone number: ").strip()
limit = input("Enter last message limit: ").strip()

# Telegram istemcisini oluştur
client = TelegramClient('session_name', apiId, apiHash)

async def main():
    #enter telegram
    await client.start(phoneNumber)
    print("Connect telegram!")

    #last 10 message and list channels
    async for dialog in client.iter_dialogs():
        if isinstance(dialog.entity, Channel):
            print(f'\Channel Name: {dialog.name}, Channel ID: {dialog.id}')
            messages = await client.get_messages(dialog.entity, limit = 10)
            for message in messages:
                print(f'Send: {message.sender_id}, Time: {message.date}, Message: {message.text}')
        
# Run telegram client
with client:
    client.loop.run_until_complete(main())

import pandas as pd
from datetime import datetime
from pyrogram import Client
import os
import re

class TelegramExtractor:
    def __init__(self):
        self.client = None
    
    def init_client(self, api_id, api_hash, bot_token):
        """تهيئة عميل Pyrogram"""
        self.client = Client("bot_session", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
        return self.client
    
    def clean_channel_name(self, channel):
        """تنظيف اسم القناة من الروابط"""
        channel = re.sub(r'https?://t\.me/', '', channel)
        channel = re.sub(r'@', '', channel)
        return channel.strip()
    
    def extract_messages(self, chat_username, limit, api_id, api_hash, bot_token):
        """استخراج الرسائل من القناة"""
        messages = []
        chat_username = self.clean_channel_name(chat_username)
        
        try:
            with self.init_client(api_id, api_hash, bot_token) as app:
                count = 0
                async for message in app.get_chat_history(chat_username, limit=limit):
                    messages.append({
                        'id': message.id,
                        'date': message.date.isoformat() if message.date else None,
                        'sender_id': str(message.from_user.id) if message.from_user else None,
                        'sender_name': message.from_user.first_name if message.from_user else None,
                        'sender_username': message.from_user.username if message.from_user else None,
                        'text': (message.text or message.caption or "").strip(),
                        'views': getattr(message, 'views', 0),
                        'forwards': getattr(message, 'forwards', 0),
                        'has_media': bool(message.media)
                    })
                    count += 1
        except Exception as e:
            raise Exception(f"خطأ في الاستخراج: {str(e)}")
        
        return messages
    
    def save_to_csv(self, data, filename=None):
        """حفظ البيانات في CSV"""
        if not filename:
            filename = f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        return filename
    
    def save_to_json(self, data, filename=None):
        """حفظ البيانات في JSON"""
        if not filename:
            filename = f"extracted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        df = pd.DataFrame(data)
        df.to_json(filename, orient='records', force_ascii=False, indent=2)
        return filename

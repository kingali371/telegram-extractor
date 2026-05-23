import os
import re
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from utils import TelegramExtractor

# تحميل المتغيرات
load_dotenv()

# ============= الإعدادات =============
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
OWNER_ID = int(os.getenv('OWNER_ID', 0))

# قائمة الأدمن
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
if OWNER_ID and OWNER_ID not in ADMIN_IDS:
    ADMIN_IDS.append(OWNER_ID)

extractor = TelegramExtractor()

# ============= دوال المساعدة =============
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def save_admins():
    try:
        with open('admins.txt', 'w') as f:
            for aid in ADMIN_IDS:
                if aid != OWNER_ID:
                    f.write(f"{aid}\n")
    except:
        pass

def load_admins():
    global ADMIN_IDS
    try:
        if os.path.exists('admins.txt'):
            with open('admins.txt', 'r') as f:
                for line in f:
                    aid = int(line.strip())
                    if aid not in ADMIN_IDS and aid != OWNER_ID:
                        ADMIN_IDS.append(aid)
    except:
        pass

# ============= الأوامر =============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    is_admin_user = is_admin(uid)
    
    text = f"""
🤖 **بوت استخراج بيانات تيليجرام**

📊 **المميزات:**
• استخراج الرسائل من القنوات
• تصدير CSV / JSON
• نظام أدمن متكامل

👤 **صلاحيتك:** {'✅ أدمن' if is_admin_user else '🔰 مستخدم عادي'}

📝 **الأوامر:**
/start - الترحيب
/id - معرفك
/help - المساعدة
"""
    
    if is_admin_user:
        text += "/extract @username [عدد] - استخراج رسائل\n"
    
    if is_owner(uid):
        text += """
🔧 **إدارة الأدمن:**
/add_admin <id> - إضافة أدمن
/remove_admin <id> - إزالة أدمن
/admins - قائمة الأدمن
/stats - إحصاءات
"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        await update.message.reply_text(f"🆔 المعرف: `{target.id}`", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"🆔 معرفك: `{update.effective_user.id}`", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
📚 **طريقة الاستخدام:**

`/extract @telegram 100`

**شرح:**
• `@telegram` - اسم القناة
• `100` - عدد الرسائل

**أمثلة:**
• `/extract @channel 50`
• `/extract https://t.me/channel 200`

**المخرجات:** ملف CSV يحتوي على:
• معرف الرسالة
• التاريخ
• المرسل
• النص
• المشاهدات
• إعادة التوجيه
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if not is_admin(uid):
        await update.message.reply_text("❌ هذا الأمر متاح للأدمن فقط!")
        return
    
    if not context.args:
        await update.message.reply_text("📝 `/extract @username [عدد]`", parse_mode='Markdown')
        return
    
    channel = context.args[0]
    limit = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 100
    
    msg = await update.message.reply_text(f"⏳ جاري استخراج {limit} رسالة...")
    
    try:
        messages = extractor.extract_messages(channel, limit, API_ID, API_HASH, BOT_TOKEN)
        
        if messages:
            filename = extractor.save_to_csv(messages)
            
            with open(filename, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=filename,
                    caption=f"✅ {len(messages)} رسالة من {channel}"
                )
            
            os.remove(filename)
            await msg.edit_text(f"✅ تم الاستخراج بنجاح! ({len(messages)} رسالة)")
        else:
            await msg.edit_text(f"❌ لا توجد رسائل في {channel}")
            
    except Exception as e:
        await msg.edit_text(f"❌ خطأ: {str(e)[:200]}")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ فقط المالك يمكنه إضافة أدمن!")
        return
    
    if not context.args:
        await update.message.reply_text("📝 /add_admin <user_id>")
        return
    
    try:
        new_id = int(context.args[0])
        if new_id in ADMIN_IDS:
            await update.message.reply_text(f"✅ المستخدم {new_id} أدمن بالفعل")
            return
        
        ADMIN_IDS.append(new_id)
        save_admins()
        await update.message.reply_text(f"✅ تم إضافة `{new_id}` كأدمن", parse_mode='Markdown')
        
        try:
            await context.bot.send_message(new_id, "🎉 تمت ترقيتك لأدمن في البوت!")
        except:
            pass
    except:
        await update.message.reply_text("❌ خطأ: معرف غير صالح")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ فقط المالك يمكنه إزالة أدمن!")
        return
    
    if not context.args:
        await update.message.reply_text("📝 /remove_admin <user_id>")
        return
    
    try:
        rem_id = int(context.args[0])
        if rem_id == OWNER_ID:
            await update.message.reply_text("❌ لا يمكن إزالة المالك!")
            return
        
        if rem_id in ADMIN_IDS:
            ADMIN_IDS.remove(rem_id)
            save_admins()
            await update.message.reply_text(f"✅ تم إزالة `{rem_id}` من الأدمن", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ {rem_id} ليس أدمن")
    except:
        await update.message.reply_text("❌ خطأ: معرف غير صالح")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ غير مصرح")
        return
    
    others = [a for a in ADMIN_IDS if a != OWNER_ID]
    text = f"👑 **المالك:** `{OWNER_ID}`\n\n👥 **الأدمن:**\n"
    text += "\n".join([f"• `{a}`" for a in others]) if others else "• لا يوجد"
    text += f"\n\n📊 **العدد:** {len(others)}"
    await update.message.reply_text(text, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ للمالك فقط")
        return
    
    text = f"""
📊 **إحصاءات البوت**

👑 **المالك:** `{OWNER_ID}`
👥 **الأدمن:** {len([a for a in ADMIN_IDS if a != OWNER_ID])}

⚙️ **الحالة:** 🟢 يعمل
📅 **التاريخ:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    await update.message.reply_text(text, parse_mode='Markdown')

# ============= التشغيل =============
if __name__ == '__main__':
    load_admins()
    if OWNER_ID and OWNER_ID not in ADMIN_IDS:
        ADMIN_IDS.append(OWNER_ID)
    
    print("=" * 40)
    print("🤖 تشغيل بوت استخراج تيليجرام")
    print(f"👑 المالك: {OWNER_ID}")
    print(f"👥 الأدمن: {len([a for a in ADMIN_IDS if a != OWNER_ID])}")
    print("=" * 40)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("extract", extract))
    app.add_handler(CommandHandler("add_admin", add_admin))
    app.add_handler(CommandHandler("remove_admin", remove_admin))
    app.add_handler(CommandHandler("admins", list_admins))
    app.add_handler(CommandHandler("stats", stats))
    
    print("✅ البوت يعمل...")
    app.run_polling()

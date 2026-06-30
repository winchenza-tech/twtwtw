import os
import json
import re
from datetime import datetime, timedelta
import pytz
import tweepy
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types
from apscheduler.schedulers.background import BackgroundScheduler

# 1. Ortam Değişkenleri
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 2. İstemciler
client_gemini = genai.Client(api_key=GEMINI_API_KEY)
tg_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

twitter_client = tweepy.Client(
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

current_tweets = []

def fetch_and_send_to_telegram():
    global current_tweets
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    current_hour = now.hour

    # Sabah 7 ile gece 01:00 arası izinli (01:00 - 06:59 arası sessiz)
    if 1 <= current_hour < 7:
        print(f"[{now.strftime('%H:%M:%S')}] Sessizlik modu aktif, işlem atlandı.")
        return

    print("Ceminay sevdiğin eski prompt ve canlı aramayla gündemi tarıyor...")

    try:
        # Sistem çökmesin diye arka plandaki teknik JSON talimatı
        system_instruction = (
            "ÇIKTI FORMATI: Uygulamanın bozulmaması için cevabın SADECE VE SADECE geçerli bir JSON array (liste) formatında olmalıdır. "
            "Başka hiçbir açıklama, giriş veya kapanış cümlesi ekleme.\n"
            'Örnek Çıktı: ["tweet 1", "tweet 2", "tweet 3", "tweet 4", "tweet 5", "tweet 6"]'
        )

        # Düzenlenen eski başarılı promptun
        prompt = (
            "Şu anki gerçek Türkiye ve dünya gündemini, sosyal medyada yapay veya bot hesaplarca şişirilmemiş, "
            "insanların gerçekten konuştuğu somut ve gerçek konuları analiz et. "
            "Bu konulardan beslenerek; son derece esprili, muzip, ironik, akıl dolu ve zeki TAM 6 FARKLI tweet üret.\n\n"
            "Kural 1: Her bir tweet kesinlikle EN FAZLA 21 KELİME olsun.\n"
            "Kural 2: Yapay zeka gibi kokmasın, samimi ve sarkastik bir insan yazmış gibi olsun.\n"
            "Kural 3: Hashtag (#) kullanma veya çok nadir, espriye dahilse kullan.\n"
            "Sadece tweet metnilerini döndür, başında veya sonunda başka açıklama olmasın."
        )

        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[{"google_search": {}}],
            )
        )
        
        raw_text = response.text.strip()
        json_match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        
        if json_match:
            clean_text = json_match.group(0)
        else:
            clean_text = raw_text

        current_tweets = json.loads(clean_text)

        # Telegram menüsü
        msg_text = "✨ *Ceminay Seçenekleri Hazırladı!*\n\n"
        msg_text += "🚀 Paylaşmak için butonları kullanabilirsin.\n"
        msg_text += "✏️ *Düzenlemek istersen:* Sohbete sadece tweetin numarasını (örn: 2) yazıp yolla.\n\n"
        
        for i, t in enumerate(current_tweets):
            msg_text += f"*{i+1}. Seçenek:*\n{t}\n\n"

        # 6 Butonlu tasarım
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("1️⃣", callback_data="tweet_0"),
            InlineKeyboardButton("2️⃣", callback_data="tweet_1"),
            InlineKeyboardButton("3️⃣", callback_data="tweet_2")
        )
        markup.row(
            InlineKeyboardButton("4️⃣", callback_data="tweet_3"),
            InlineKeyboardButton("5️⃣", callback_data="tweet_4"),
            InlineKeyboardButton("6️⃣", callback_data="tweet_5")
        )
        markup.row(InlineKeyboardButton("❌ Hiçbirini Beğenmedim (İptal)", callback_data="cancel"))

        tg_bot.send_message(TELEGRAM_CHAT_ID, msg_text, reply_markup=markup, parse_mode="Markdown")
        print("Telegram'a 6 eski usul seçenek başarıyla gönderildi.")

    except Exception as e:
        error_msg = f"⚠️ Gemini'den veri çekerken hata oluştu:\n{e}"
        print(error_msg)
        tg_bot.send_message(TELEGRAM_CHAT_ID, error_msg)


@tg_bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    global current_tweets
    
    if call.data == "cancel":
        tg_bot.edit_message_text(
            "❌ *İptal edildi.* Bu periyotta tweet atılmayacak.", 
            call.message.chat.id, 
            call.message.message_id, 
            parse_mode="Markdown"
        )
        return

    if call.data.startswith("tweet_"):
        idx = int(call.data.split("_")[1])
        
        if not current_tweets or idx >= len(current_tweets):
            tg_bot.answer_callback_query(call.id, "⚠️ Bu tweetlerin süresi dolmuş veya liste bulunamadı.")
            return

        selected_tweet = current_tweets[idx]

        try:
            twitter_client.create_tweet(text=selected_tweet)
            success_msg = f"✅ *BAŞARIYLA PAYLAŞILDI!*\n\n{selected_tweet}"
            tg_bot.edit_message_text(
                success_msg, 
                call.message.chat.id, 
                call.message.message_id, 
                parse_mode="Markdown"
            )
            print("Tweet başarıyla paylaşıldı.")
            
        except Exception as e:
            tg_bot.edit_message_text(
                f"⚠️ *X'e gönderirken hata oluştu:*\n{e}", 
                call.message.chat.id, 
                call.message.message_id, 
                parse_mode="Markdown"
            )

@tg_bot.message_handler(func=lambda message: message.text.strip() in ["1", "2", "3", "4", "5", "6"])
def handle_edit_request(message):
    global current_tweets
    if not current_tweets:
        tg_bot.reply_to(message, "⚠️ Şu an düzenlenecek aktif bir tweet listesi yok.")
        return
        
    idx = int(message.text.strip()) - 1
    if idx >= len(current_tweets):
        tg_bot.reply_to(message, "⚠️ Hatalı numara girdin.")
        return
        
    selected_tweet = current_tweets[idx]
    
    msg = tg_bot.reply_to(
        message, 
        f"✏️ *{idx+1}. Seçeneği Düzenliyorsun!*\n\n"
        f"Mevcut metin:\n`{selected_tweet}`\n\n"
        f"Lütfen X'te paylaşılmasını istediğin **YENİ metni** buraya yazıp gönder. (İşlemi iptal etmek için sohbete 'iptal' yazabilirsin):", 
        parse_mode="Markdown"
    )
    tg_bot.register_next_step_handler(msg, process_new_tweet)

def process_new_tweet(message):
    if message.text.lower().strip() == 'iptal':
        tg_bot.reply_to(message, "❌ Düzenleme işlemi iptal edildi.")
        return
        
    new_text = message.text.strip()
    
    try:
        twitter_client.create_tweet(text=new_text)
        tg_bot.reply_to(message, f"✅ *DÜZENLENMİŞ TWEET BAŞARIYLA PAYLAŞILDI!*\n\n{new_text}", parse_mode="Markdown")
        print("Düzenlenmiş manuel tweet paylaşıldı.")
    except Exception as e:
        tg_bot.reply_to(message, f"⚠️ *X'e gönderirken hata oluştu:*\n{e}", parse_mode="Markdown")


if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    
    start_time = now + timedelta(seconds=10)
        
    print(f"Ceminay Klasik Modda Başladı! İlk üretim saati: {start_time.strftime('%H:%M:%S')}")

    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        fetch_and_send_to_telegram, 
        'interval', 
        minutes=85, 
        start_date=start_time
    )
    scheduler.start()

    try:
        tg_bot.delete_webhook(drop_pending_updates=True)
        tg_bot.infinity_polling(allowed_updates=["message", "callback_query"])
    except (KeyboardInterrupt, SystemExit):
        print("Bot durduruldu.")

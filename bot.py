import os
import json
from datetime import datetime, timedelta
import pytz
import tweepy
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from google.genai import types  # Canlı arama için eklendi
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

    if 1 <= current_hour < 7:
        print(f"[{now.strftime('%H:%M:%S')}] Sessizlik modu aktif, işlem atlandı.")
        return

    print("Gemini 2.5 Flash canlı arama yaparak gündemi tarıyor...")

    try:
        prompt = (
            "Şu an Türkiye internetinde, sosyal medyasında (X, Ekşi Sözlük, Instagram) insanların GERÇEKTEN konuştuğu "
            "en güncel, somut, popüler kültür, spor, magazin veya absürt olayları Google üzerinde ara ve analiz et.\n\n"
            "ÖNEMLİ KISITLAMA: Sürekli aynı şeyleri döndürme. Eğer çok ekstrem bir gelişme yoksa EKONOMİ, DOLAR, ENFLASYON, "
            "MAAŞLAR gibi bayatlamış ve herkesin sürekli yazdığı klişe konuları PAS GEÇ. Odak noktan güncel popüler tartışmalar, "
            "sosyal medya geyikleri ve absürt yerel haberler olsun.\n\n"
            "Bu konulardan beslenerek TAM 4 FARKLI tweet seçeneği üret.\n\n"
            "TON VE ÜSLUP FİLTRESİ:\n"
            "- Zeki, hafif umursamaz, alaycı ve ince ironiler yapan gerçek bir X (Twitter) kullanıcısı gibi yaz.\n"
            "- KESİNLİKLE yapay zeka olduğunu belli eden 'didaktik', 'öğretici' veya 'fark ettiniz mi?' gibi bayat giriş yapıları kullanma.\n"
            "- LinkedIn tarzı aşırı hevesli, 'bot kokan' esprilerden uzak dur. Cümlelerin sanki bir insan o an sinirlenip veya eğlenip "
            "klavyeye rastgele fırlatmış gibi organik, doğal ve samimi olsun.\n\n"
            "KESİN KURALLAR:\n"
            "1. KESİNLİKLE hashtag (#) kullanma.\n"
            "2. Her bir tweet metni KESİNLİKLE EN FAZLA 19 KELİME uzunluğunda olmalıdır.\n"
            "3. ÇIKTI FORMATI: Sadece ve sadece geçerli bir JSON dizisi (array) döndür. Başka hiçbir açıklama veya markdown (```json) kullanma.\n\n"
            'Örnek Çıktı: ["birinci zeki tweet", "ikinci ironik tweet", "üçüncü muzip tweet", "dördüncü sivri tweet"]'
        )

        # Gemini'ye Google Search (Canlı Arama) yeteneği veriliyor
        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],  # Canlı arama motoru aktif!
            )
        )
        
        clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        current_tweets = json.loads(clean_text)

        msg_text = "✨ Ceminay CANLI Gündemi Taradı! Hangisini X'te paylaşalım?\n\n"
        for i, t in enumerate(current_tweets):
            msg_text += f"*{i+1}. Seçenek:*\n{t}\n\n"

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("1️⃣", callback_data="tweet_0"),
            InlineKeyboardButton("2️⃣", callback_data="tweet_1"),
            InlineKeyboardButton("3️⃣", callback_data="tweet_2"),
            InlineKeyboardButton("4️⃣", callback_data="tweet_3")
        )
        markup.row(InlineKeyboardButton("❌ Hiçbirini Beğenmedim (İptal)", callback_data="cancel"))

        tg_bot.send_message(TELEGRAM_CHAT_ID, msg_text, reply_markup=markup, parse_mode="Markdown")
        print("Telegram'a canlı arama sonuçları gönderildi.")

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


if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    
    start_time = now + timedelta(seconds=10)
        
    print(f"Ceminay Onay Sistemi Başladı! (Canlı Google Arama Aktif) İlk üretim saati: {start_time.strftime('%H:%M:%S')}")

    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        fetch_and_send_to_telegram, 
        'interval', 
        minutes=85, 
        start_date=start_time
    )
    scheduler.start()

    try:
        tg_bot.infinity_polling()
    except (KeyboardInterrupt, SystemExit):
        print("Bot durduruldu.")

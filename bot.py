import os
import json
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

    if 1 <= current_hour < 7:
        print(f"[{now.strftime('%H:%M:%S')}] Sessizlik modu aktif, işlem atlandı.")
        return

    print("Gemini 2.5 Flash sosyal medyadaki viral formatları tarıyor...")

    try:
        # Prompt, yapay zeka kalıplarını kırmak için tamamen baştan yazıldı
        prompt = (
            "Google üzerinde şu an Türkiye sosyal medyasında (X/Twitter, Ekşi Sözlük vb.) çok etkileşim almış, "
            "insanların beğendiği, paylaştığı popüler ve güncel 15 farklı tweet/post örneğini veya mizah formatını incele.\n\n"
            "GÖREV:\n"
            "Bu popüler postların mizahi yapısını, konuşma tarzını, alaycı üslubunu ve kelime oyunlarını analiz et. "
            "Onların tarzından beslenerek, ama KESİNLİKLE aynısı olmayan, şu anki güncel Türkiye/dünya gündemine uyarlanmış "
            "TAM 4 FARKLI tweet seçeneği üret.\n\n"
            "KRİTİK TARZ VE ÜSLUP KURALLARI:\n"
            "- Ekonomi, dolar, enflasyon gibi artık klişeleşmiş ve herkesin her saniye yazdığı konuları (çok büyük bir kırılma yoksa) PAS GEÇ. "
            "Sosyal medyanın gerçek geyiklerine, popüler kültür tartışmalarına, spor veya absürt magazin olaylarına odaklan.\n"
            "- Bir yapay zeka gibi 'didaktik', 'öğretici' veya 'fark ettiniz mi?' tarzı girişler KESİNLİKLE yasaktır.\n"
            "- Cümleler tıpkı gerçek bir insanın X'te yazdığı gibi olsun: İntro yok, hazırlık yok, direkt konunun ortasından, "
            "hafif umursamaz, aşırı zeki ve muzip bir vuruşla başlasın. Kelimeleri özenle seçilmiş, rafine bir mizah olsun.\n\n"
            "KESİN SINIRLAR:\n"
            "1. KESİNLİKLE hashtag (#) kullanma.\n"
            "2. Her bir tweet metni KESİNLİKLE EN FAZLA 19 KELİME uzunluğunda olmalıdır.\n"
            "3. ÇIKTI FORMATI: Sadece ve sadece geçerli bir JSON dizisi (array) döndür. Başka hiçbir açıklama, markdown (```json) kullanma.\n\n"
            'Örnek Çıktı: ["birinci zeki tweet", "ikinci viral tarzda tweet", "üçüncü muzip tweet", "dördüncü özgün tweet"]'
        )

        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
            )
        )
        
        clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        current_tweets = json.loads(clean_text)

        msg_text = "✨ Ceminay Viral Formatları Taradı! Hangisini X'te paylaşalım?\n\n"
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
        print("Telegram'a viral formatlı alternatifler gönderildi.")

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
        
    print(f"Ceminay Onay Sistemi Başladı! (Viral Analiz Aktif) İlk üretim saati: {start_time.strftime('%H:%M:%S')}")

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

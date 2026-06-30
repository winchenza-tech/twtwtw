import os
import json
from datetime import datetime, timedelta
import pytz
import tweepy
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
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

# Üretilen tweetleri geçici hafızada tutacağımız liste
current_tweets = []

def fetch_and_send_to_telegram():
    global current_tweets
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    current_hour = now.hour

    # Gece 01:00 ile sabah 07:00 arası sessizlik kontrolü
    if 1 <= current_hour < 7:
        print(f"[{now.strftime('%H:%M:%S')}] Sessizlik modu (01:00 - 07:00 arası aktif), işlem atlandı.")
        return

    print("Gemini 2.5 Flash'tan 4 seçenekli tweet isteniyor...")

    try:
        prompt = (
            "Şu anki gerçek Türkiye ve dünya gündemini analiz et. Sadece trollerin veya bot hesapların şişirdiği "
            "suni etiketleri (hashtag) değil, sokaktaki gerçek insanın konuştuğu organik ve somut konuları baz al. "
            "Bu konulardan beslenerek TAM 4 FARKLI tweet seçeneği üret.\n\n"
            "KARAKTER VE TON: Çok zeki, gündemi yakından takip eden, muzip, hafif alaycı ve ince ironiler yapan bir insansın. "
            "Kesinlikle yapay zeka gibi 'robotik', 'didaktik' veya 'aşırı coşkulu' kalıplar kullanma. 'Şunu fark ettiniz mi?', "
            "'İşte günün gerçeği' gibi bayat girişlerden ve klişe esprilerden uzak dur. Sıradan ama sivri dilli bir insanın "
            "anlık aklına gelen, umursamaz ama akıl dolu bir düşüncesi gibi yaz.\n\n"
            "KESİN KURALLAR:\n"
            "1. KESİNLİKLE hashtag (#) kullanma.\n"
            "2. Her bir tweet metni KESİNLİKLE EN FAZLA 19 KELİME uzunluğunda olmalıdır. (Kısa, net ve vurucu ol).\n"
            "3. ÇIKTI FORMATI: Sadece ve sadece geçerli bir JSON dizisi (array) döndür. Başka hiçbir açıklama, sohbet veya markdown (```json vb.) kullanma.\n\n"
            'Örnek Çıktı: ["birinci zeki tweet metni", "ikinci ironik tweet metni", "üçüncü muzip tweet", "dördüncü sivri tweet"]'
        )

        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        # JSON dizisini temizleyip listeye çevirme
        clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        current_tweets = json.loads(clean_text)

        # Telegram Mesajı Hazırlığı
        msg_text = "✨ Ceminay Gündemi Taradı! Hangisini X'te paylaşalım?\n\n"
        for i, t in enumerate(current_tweets):
            msg_text += f"*{i+1}. Seçenek:*\n{t}\n\n"

        # Butonlar
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("1️⃣", callback_data="tweet_0"),
            InlineKeyboardButton("2️⃣", callback_data="tweet_1"),
            InlineKeyboardButton("3️⃣", callback_data="tweet_2"),
            InlineKeyboardButton("4️⃣", callback_data="tweet_3")
        )
        markup.row(InlineKeyboardButton("❌ Hiçbirini Beğenmedim (İptal)", callback_data="cancel"))

        tg_bot.send_message(TELEGRAM_CHAT_ID, msg_text, reply_markup=markup, parse_mode="Markdown")
        print("Telegram'a seçenekler gönderildi, onay bekleniyor...")

    except Exception as e:
        error_msg = f"⚠️ Gemini'den veri çekerken hata oluştu:\n{e}"
        print(error_msg)
        tg_bot.send_message(TELEGRAM_CHAT_ID, error_msg)


# Telegram Buton Tıklamalarını Dinleyen Fonksiyon
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
            # X'e gönder
            twitter_client.create_tweet(text=selected_tweet)
            
            # Telegram mesajını güncelle
            success_msg = f"✅ *BAŞARIYLA PAYLAŞILDI!*\n\n{selected_tweet}"
            tg_bot.edit_message_text(
                success_msg, 
                call.message.chat.id, 
                call.message.message_id, 
                parse_mode="Markdown"
            )
            print("Kullanıcı seçimi yaptı, tweet atıldı.")
            
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
    
    # Sunucu başlatıldıktan 10 saniye sonra ilk döngüyü hemen başlatır
    start_time = now + timedelta(seconds=10)
        
    print(f"Ceminay Onay Sistemi Başladı! (Gemini 2.5 Flash) İlk üretim saati: {start_time.strftime('%H:%M:%S')}")

    # Zamanlayıcı arka planda çalışır
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        fetch_and_send_to_telegram, 
        'interval', 
        minutes=85, 
        start_date=start_time
    )
    scheduler.start()

    # Telegram botunu dinlemeye başla
    try:
        tg_bot.infinity_polling()
    except (KeyboardInterrupt, SystemExit):
        print("Bot durduruldu.")

import os
from datetime import datetime, timedelta
import pytz
import tweepy
from google import genai
from apscheduler.schedulers.blocking import BlockingScheduler

# 1. Ortam Değişkenlerini Yükle
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# 2. İstemcileri Başlat
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# Kesintisiz bağlantı sağlayan klasik 4 anahtarlı yapı (Read/Write izinli)
twitter_client = tweepy.Client(
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_SECRET
)

def generate_and_post_tweet():
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    current_hour = now.hour

    # Gece 01:00 ile 10:00 arası sessizlik kontrolü
    if 1 <= current_hour < 10:
        print(f"[{now.strftime('%H:%M:%S')}] Saat {current_hour}:00. Gece sessizlik modu aktif, tweet atılmadı.")
        return

    print(f"[{now.strftime('%H:%M:%S')}] Gündem taranıyor ve tweet hazırlanıyor...")

    try:
        prompt = (
            "Şu anki gerçek Türkiye ve dünya gündemini, sosyal medyada yapay veya bot hesaplarca şişirilmemiş, "
            "insanların gerçekten konuştuğu somut ve gerçek konuları analiz et. "
            "Bu konulardan biri hakkında; son derece esprili, muzip, ironik, akıl dolu ve zeki bir tweet üret. "
            "Kural 1: Tweet kesinlikle 280 karakteri geçmesin. "
            "Kural 2: Yapay zeka gibi kokmasın, samimi ve sarkastik bir insan yazmış gibi olsun. "
            "Kural 3: Hashtag (#) kullanma veya çok nadir, espriye dahilse kullan. "
            "Sadece tweet metnini döndür, başında veya sonunda başka açıklama olmasın."
        )

        response = client_gemini.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        tweet_text = response.text.strip()

        if tweet_text.startswith('"') and tweet_text.endswith('"'):
            tweet_text = tweet_text[1:-1]

        # Tweeti gönder
        twitter_client.create_tweet(text=tweet_text)
        print(f"Tweet başarıyla paylaşıldı:\n👉 {tweet_text}")

    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    
    # Hedef saati 00:11 olarak ayarla
    start_time = now.replace(hour=0, minute=11, second=0, microsecond=0)
    
    # Kodu yüklediğinde saat 00:11'i geçmişse zamanlayıcıyı hemen 1 dakika sonrasına kurar
    if start_time < now:
        start_time = now + timedelta(minutes=1)
        print(f"Saat 00:11 geçtiği için telafi olarak ilk tweet {start_time.strftime('%H:%M:%S')} saatinde atılacak.")
    else:
        print(f"Bot başlatıldı... İlk tweet saati tam: {start_time.strftime('%H:%M')} -> Tekrar: 85 dakikada bir.")

    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(
        generate_and_post_tweet, 
        'interval', 
        minutes=85, 
        start_date=start_time
    )
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Bot durduruldu.")

import os
import time
from datetime import datetime
import pytz
import tweepy
from google import genai
from apscheduler.schedulers.blocking import BlockingScheduler

# 1. Ortam Değişkenlerini Yükle
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWITTER_OAUTH2_ACCESS_TOKEN = os.getenv("TWITTER_OAUTH2_ACCESS_TOKEN")

# 2. API Bağlantılarını Başlat
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

# En güncel ve resmi OAuth 2.0 v2 İstemcisi
twitter_client = tweepy.Client(bearer_token=TWITTER_OAUTH2_ACCESS_TOKEN)

def generate_and_post_tweet():
    tz = pytz.timezone('Europe/Istanbul')
    now = datetime.now(tz)
    current_hour = now.hour

    # Gece 01:00 ile 10:00 arası tweet atmama kontrolü
    if 1 <= current_hour < 10:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Saat {current_hour}:00. Gece sessizlik modu aktif, tweet atılmadı.")
        return

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Gündem taranıyor ve tweet hazırlanıyor...")

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
            model='gemini-2.5-flash',
            contents=prompt,
        )
        tweet_text = response.text.strip()

        if tweet_text.startswith('"') and tweet_text.endswith('"'):
            tweet_text = tweet_text[1:-1]

        # Twitter API v2 ile Tweet Paylaşımı
        twitter_client.create_tweet(text=tweet_text)
        print(f"Tweet başarıyla paylaşıldı:\n👉 {tweet_text}")

    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == "__main__":
    tz = pytz.timezone('Europe/Istanbul')
    
    # Bugünün tarihini alıp saati 23:23'e kuruyoruz
    start_time = datetime.now(tz).replace(hour=23, minute=59, second=0, microsecond=0)
    
    print(f"Bot başlatıldı... İlk zamanlama ayarı: {start_time.strftime('%H:%M')} -> Tekrar: 85 dakikada bir.")

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

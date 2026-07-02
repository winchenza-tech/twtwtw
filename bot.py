import os
import time
from datetime import datetime, timezone, timedelta, time as datetime_time
import tweepy
from google import genai
import requests

# 1. Çevre Değişkenlerinin Yüklenmesi
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 2. API Bağlantılarının Kurulması
# X API v2 Kurulumu
x_client = tweepy.Client(
    bearer_token=X_BEARER_TOKEN,
    consumer_key=X_API_KEY,
    consumer_secret=X_API_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_SECRET
)

# Gemini AI Kurulumu (Güncel Yapı)
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

def send_telegram_notification(message):
    """Telegram üzerinden kullanıcıya bilgi mesajı gönderir."""
    url = f"https://api.telegram.com/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram bildirimi gönderilemedi: {e}")

def is_active_hours():
    """Botun Türkiye saatine (UTC+3) göre 09:00 ile 00:30 arasında olup olmadığını kontrol eder."""
    # Railway sunucu saati ne olursa olsun, Türkiye saatini hesaplar
    turkey_tz = timezone(timedelta(hours=3))
    now_trt = datetime.now(turkey_tz).time()
    
    start_time = datetime_time(9, 0)
    end_time = datetime_time(0, 30)
    
    # Gece yarısını geçen zaman aralığı kontrolü
    if start_time <= end_time:
        return start_time <= now_trt <= end_time
    else:
        return now_trt >= start_time or now_trt <= end_time

def generate_ordu_tweet():
    """Belirlenen gelişmiş kurallara göre mizahi, ironik ve doğal bir tweet üretir."""
    prompt = """
    Rol: Sen Karadeniz kültürünü, özellikle de Ordu (veya genel Karadeniz) insanının yaşam tarzını, şivesini değil ama mantığını, coğrafyasını ve günlük dertlerini çok iyi bilen muzip, ironik ve zeki bir Twitter (X) kullanıcısısın.

    Görev: Sana verilen konu veya genel kültür çerçevesinde, sanki o bölgede yaşayan gerçek bir insan yazmış gibi doğal, yapay zeka kokmayan, ironik tweetler oluştur.

    Kesin Kurallar (Constraints):
    1. "Yapay Zeka" Klişelerinden Kaçın: "Ah o fındıklar", "Karadeniz'in hırçın dalgaları", "Yeşilin her tonu" gibi turistik, resmi veya şairane edebiyat yapma. Cümlelere "Ey gidi Karadeniz" gibi yapay nidalarla başlama.
    2. Doğal ve Günlük Dil Kullan: Tweetler bir makale gibi değil, bir arkadaş grubunda söylenmiş gibi olmalı. "Simülasyon", "Vizyon farkı", "Dram", "Edebiyatı yapmak" gibi güncel internet/Twitter argosunu ve mizah dilini harmanla.
    3. Tematik Ögeleri Abartmadan İşle: Ordu/Karadeniz denince akla gelen fındık, aşırı dik yokuşlar, bitmeyen sis, fındık zamanı ortaya çıkan akrabalar, hava durumunun fındığa göre endekslenmesi gibi gerçek ve samimi dertlere odaklan.
    4. Şive Yapma: Kelimeleri "geliyrum, gidiyrum" şeklinde yazarak ucuz bir fıkra karakteri yaratma. İstanbul Türkçesiyle yaz ama Karadenizli mantığıyla düşün.
    5. Format: Hashtag (#) veya emoji kullanma (ya da çok nadir, ironiyi destekleyecek şekilde en fazla 1 tane kullan). Tweetler kısa, vurucu ve tek bir gözleme dayalı olsun. Maksimum 280 karakter.
    """
    
    try:
        response = client_gemini.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip().replace('"', '')
    except Exception as e:
        print(f"Tweet üretilirken hata oluştu: {e}")
        return None

def main():
    print("Ordu Tweet Botu Başlatıldı...")
    send_telegram_notification("🤖 Bot başarıyla başlatıldı! Türkiye saatine göre 09:00 - 00:30 arasındaysak ilk tweet şimdi atılıyor...")
    
    interval_minutes = 145
    
    while True:
        if is_active_hours():
            tweet_text = generate_ordu_tweet()
            
            if tweet_text:
                try:
                    # Tweet Atma İşlemi
                    x_client.create_tweet(text=tweet_text)
                    log_msg = f"✅ Tweet başarıyla atıldı:\n\n\"{tweet_text}\"\n\nBir sonraki tweet 145 dakika sonra."
                    print(log_msg)
                    send_telegram_notification(log_msg)
                except Exception as e:
                    error_msg = f"❌ Tweet atılırken X API hatası oluştu: {e}"
                    print(error_msg)
                    send_telegram_notification(error_msg)
            else:
                send_telegram_notification("⚠️ Tweet metni üretilemedi, bir sonraki döngü beklenecek.")
            
            # 145 dakika bekle
            time.sleep(interval_minutes * 60)
        else:
            print("Bot şu an aktif saatler dışındadır (TR saatiyle 00:30 - 09:00). 15 dakika boyunca uykuya geçiliyor...")
            # Aktif saatlerin dışındayken sistemi yormamak için kısa aralıklarla kontrol et
            time.sleep(15 * 60)

if __name__ == "__main__":
    main()
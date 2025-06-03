import os
import re
import requests
import shutil
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
import yt_dlp
import instaloader
import socket

# BOT TOKEN
BOT_TOKEN = "your_bot_token"  # <-- o'zingiznikini yozing

# Universal sticker file_id (emoji fallback)
STICKER_LOADING = "CAACAgIAAxkBAAEBVYpmuNop5ZTxqGLv0XeVIGGl_xdRLwACGQEAAladvQo7QKxPL0e28S8E"
STICKER_OK = "CAACAgIAAxkBAAEBVZJmuNoxH6phbEoFCQHCBk_taFgqHwACSQEAAladvQpgZtXqN25VKy8E"
STICKER_FAIL = "CAACAgIAAxkBAAEBVZVmuNoypBLGoexTtQ9HbX3wPe7EKgACVwEAAladvQpE0B2FiRzB9S8E"

# Instaloader sozlamalari
insta_loader = instaloader.Instaloader(
    quiet=True,
    download_pictures=True,
    download_videos=True,
    download_geotags=False,
    download_comments=False,
    save_metadata=False
)

# YouTube-dl sozlamalari
ydl_opts = {
    'format': 'best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

# Internet bor-yo'qligini tekshirish
def check_internet():
    try:
        socket.setdefaulttimeout(3)
        host = socket.gethostbyname("www.google.com")
        s = socket.create_connection((host, 80), 2)
        s.close()
        return True
    except Exception:
        return False

# Faqat URL ajratib olish
def extract_url(text):
    urls = re.findall(r'https?://\S+', text)
    return urls[0] if urls else None

# Pinterest qisqa linkdan to‘liq link olish
def get_real_pinterest_url(short_url):
    try:
        r = requests.get(short_url, allow_redirects=True, timeout=10)
        return r.url
    except Exception as e:
        print(f"Pinterest redirect xatolik: {e}")
        return None

# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Salom! Men quyidagi platformalardan <u>rasm va video</u>larni yuklab bera olaman:</b>\n\n"
        "📺 <b>YouTube</b> (faqat video)\n"
        "📸 <b>Instagram</b> (rasm+video)\n"
        "📌 <b>Pinterest</b> (rasm+video)\n\n"
        "⬇️ Post yoki video linkini yuboring! 👇",
        parse_mode="HTML"
    )

# YouTube video yuklab olish (YouTube faqat video yoki thumbnail)
def download_youtube_video(url: str, chat_id: str):
    try:
        ydl_opts['outtmpl'] = f"youtube_{chat_id}.%(ext)s"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return filename, None
    except Exception as e:
        print(f"YouTube xatolik: {e}")
        return None, None

# Instagram postdan rasm va video yuklash
def download_instagram_media(url: str, chat_id: str):
    try:
        shortcode = url.split("/")[-2]
        post = instaloader.Post.from_shortcode(insta_loader.context, shortcode)
        folder = f"insta_{chat_id}"
        insta_loader.download_post(post, target=folder)
        images, videos = [], []
        for file in os.listdir(folder):
            path = os.path.join(folder, file)
            if file.endswith(".mp4"):
                videos.append(path)
            elif file.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                images.append(path)
        return images, videos, folder
    except Exception as e:
        print(f"Instagram xatolik: {e}")
        return [], [], None

# Pinterest postdan rasm va video yuklash
def download_pinterest_media(url: str, chat_id: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Rasm
        img_tag = soup.find('img')
        image_path = None
        if img_tag and img_tag.get('src'):
            img_url = img_tag['src']
            image_path = f"pinterest_{chat_id}.jpg"
            r = requests.get(img_url, stream=True)
            with open(image_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Video
        video_tag = soup.find('video')
        video_path = None
        if video_tag:
            video_url = video_tag.get('src') or (video_tag.find('source').get('src') if video_tag.find('source') else None)
            if video_url:
                video_path = f"pinterest_{chat_id}.mp4"
                r = requests.get(video_url, stream=True, headers=headers)
                with open(video_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

        return image_path, video_path
    except Exception as e:
        print(f"Pinterest xatolik: {e}")
        return None, None

# Sticker ishlamasa emoji
async def safe_sticker(update, sticker_id):
    try:
        await update.message.reply_sticker(sticker_id)
    except Exception:
        await update.message.reply_text("⏳")

# Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not check_internet():
        await update.message.reply_text("❗️ Internetingiz ishlamayapti yoki DNS xato. Internetni yoqing va yana urinib ko‘ring.")
        return

    text = update.message.text
    url = extract_url(text)
    chat_id = str(update.message.chat_id)

    if not url:
        await update.message.reply_text("To‘g‘ri video yoki rasm linkini yuboring!")
        return

    # YouTube (faqat video)
    if "youtube.com" in url or "youtu.be" in url:
        await safe_sticker(update, STICKER_LOADING)
        await update.message.reply_text("⏳ YouTube videoni yuklab olyapman. Iltimos, kuting...", parse_mode="HTML")
        video_path, _ = download_youtube_video(url, chat_id)
        if video_path:
            await safe_sticker(update, STICKER_OK)
            await update.message.reply_text("✅ <b>YouTube videosi tayyor!</b>", parse_mode="HTML")
            await update.message.reply_video(video=open(video_path, "rb"))
            os.remove(video_path)
        else:
            await safe_sticker(update, STICKER_FAIL)
            await update.message.reply_text("❌ <b>YouTube videosini yuklab bo'lmadi.</b>\nYana urinib ko‘ring!", parse_mode="HTML")
        return

    # Instagram (rasm va video)
    elif "instagram.com" in url:
        await safe_sticker(update, STICKER_LOADING)
        await update.message.reply_text("⏳ Instagramdan media yuklab olyapman. Iltimos, kuting...", parse_mode="HTML")
        images, videos, folder = download_instagram_media(url, chat_id)
        if images or videos:
            await safe_sticker(update, STICKER_OK)
            if images:
                await update.message.reply_text(f"🖼 {len(images)} ta rasm yuklandi:")
                for img in images:
                    await update.message.reply_photo(photo=open(img, "rb"))
            if videos:
                await update.message.reply_text(f"🎬 {len(videos)} ta video yuklandi:")
                for vid in videos:
                    await update.message.reply_video(video=open(vid, "rb"))
            if folder and os.path.exists(folder):
                shutil.rmtree(folder)
        else:
            await safe_sticker(update, STICKER_FAIL)
            await update.message.reply_text("❌ <b>Instagram mediasini yuklab bo'lmadi.</b>", parse_mode="HTML")
        return

    # Pinterest (rasm va video)
    elif "pinterest." in url or "pin.it" in url:
        await safe_sticker(update, STICKER_LOADING)
        await update.message.reply_text("⏳ Pinterestdan media yuklab olyapman. Iltimos, kuting...", parse_mode="HTML")
        # Qisqa link bo'lsa, to‘liq linkka aylantirish
        if "pin.it" in url:
            url = get_real_pinterest_url(url)
            if not url or "pinterest.com/pin/" not in url:
                await safe_sticker(update, STICKER_FAIL)
                await update.message.reply_text(
                    "❌ <b>Qisqa Pinterest linkdan postni aniqlab bo‘lmadi.</b>\n"
                    "Iltimos, postning to‘liq linkini yuboring (https://www.pinterest.com/pin/...)",
                    parse_mode="HTML"
                )
                return
        image_path, video_path = download_pinterest_media(url, chat_id)
        if image_path or video_path:
            await safe_sticker(update, STICKER_OK)
            if image_path:
                await update.message.reply_text("🖼 Rasm yuklandi:")
                await update.message.reply_photo(photo=open(image_path, "rb"))
                os.remove(image_path)
            if video_path:
                await update.message.reply_text("🎬 Video yuklandi:")
                await update.message.reply_video(video=open(video_path, "rb"))
                os.remove(video_path)
        else:
            await safe_sticker(update, STICKER_FAIL)
            await update.message.reply_text(
                "❌ <b>Pinterest mediasini yuklab bo‘lmadi.</b>\n"
                "Videoli yoki rasimli post bo‘lishi shart!", parse_mode="HTML"
            )
        return

    else:
        await update.message.reply_text(
            "⚠️ <b>Noto'g'ri link!</b>\n"
            "Foydalanish uchun quyidagi platformalardan birining post/video/rasm linkini yuboring:\n\n"
            "• <b>YouTube</b>\n• <b>Instagram</b>\n• <b>Pinterest</b>",
            parse_mode="HTML"
        )

# Main
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == "__main__":
    main()

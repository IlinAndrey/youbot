import os
import yt_dlp
import telebot
from googleapiclient.discovery import build
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')
youtube_api_key = os.getenv('YOUTUBE_API_KEY')

bot = telebot.TeleBot(bot_token)
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

app = FastAPI()

def search_youtube(query, max_results=4, page_token=None):
    search_response = youtube.search().list(
        q=query,
        type='video',
        part='snippet',
        maxResults=max_results,
        pageToken=page_token
    ).execute()

    videos = []
    for search_result in search_response.get('items', []):
        video_data = {
            'title': search_result['snippet']['title'],
            'video_id': search_result['id']['videoId'],
            'thumbnail': search_result['snippet']['thumbnails']['high']['url']
        }
        videos.append(video_data)

    next_page_token = search_response.get('nextPageToken', None)
    return videos, next_page_token

def send_video_options(chat_id, query, videos, next_page_token):
    markup = InlineKeyboardMarkup()

    for index, video in enumerate(videos):
        button_text = f"{index + 1}. {video['title']}"
        video_button = InlineKeyboardButton(button_text, callback_data=video['video_id'])
        markup.add(video_button)

    if next_page_token:
        next_button = InlineKeyboardButton("Следующие 4 видео", callback_data=f"next_{next_page_token}_{query}")
        markup.add(next_button)

    for video in videos:
        bot.send_photo(chat_id, video['thumbnail'], caption=video['title'])

    bot.send_message(chat_id, "Выберите видео:", reply_markup=markup)

def get_video_url(youtube_url):
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            video_url = info_dict.get('url', None)
            return video_url
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith('next_'):
        _, next_page_token, query = call.data.split('_', 2)  # Получаем токен страницы и исходный запрос
        videos, next_page_token = search_youtube(query, page_token=next_page_token)
        send_video_options(call.message.chat.id, query, videos, next_page_token)
    else:
        video_id = call.data
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        video_url = get_video_url(youtube_url)

        if video_url:
            bot.send_message(call.message.chat.id, f"Видео найдено. Вот ссылка на видео: {video_url}")
        else:
            bot.send_message(call.message.chat.id, "Не удалось получить видео. Попробуйте снова.")

@app.post("/webhook")
async def process_webhook(request: Request):
    data = await request.json()
    update = telebot.types.Update.de_json(data)

    if update.message:
        query = update.message.text
        videos, next_page_token = search_youtube(query)
        send_video_options(update.message.chat.id, query, videos, next_page_token)

    if update.callback_query:
        bot.process_new_callback_query([update.callback_query])

    return {"status": "ok"}

@app.get("/")
def index():
    return {"message": "Hello World"}

@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv('WEBHOOK_URL')
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

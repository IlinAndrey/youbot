import os
import yt_dlp
from googleapiclient.discovery import build
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')
youtube_api_key = os.getenv('YOUTUBE_API_KEY')

bot = Bot(token=bot_token)
youtube = build('youtube', 'v3', developerKey=youtube_api_key)
app = FastAPI()

class TelegramWebhook(BaseModel):
    update_id: int
    message: dict

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

@app.post("/webhook")
async def webhook(webhook_data: TelegramWebhook):
    update = Update.de_json(webhook_data.dict(), bot)

    if update.message:
        chat_id = update.message.chat.id
        query = update.message.text

        videos, next_page_token = search_youtube(query)
        markup = build_inline_keyboard(videos, next_page_token, query)

        for video in videos:
            bot.send_photo(chat_id, video['thumbnail'], caption=video['title'])
        
        bot.send_message(chat_id, "Выберите видео:", reply_markup=markup)

    return JSONResponse(content={"message": "ok"})

def build_inline_keyboard(videos, next_page_token, query):
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()

    for index, video in enumerate(videos):
        button_text = f"{index + 1}. {video['title']}"
        video_button = InlineKeyboardButton(button_text, callback_data=video['video_id'])
        markup.add(video_button)

    if next_page_token:
        next_button = InlineKeyboardButton("Следующие 4 видео", callback_data=f"next_{next_page_token}_{query}")
        markup.add(next_button)

    return markup

@app.get("/")
async def index():
    return {"message": "Hello World"}

import os
import yt_dlp
import logging
from googleapiclient.discovery import build
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_webhook
from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot_token = os.getenv('BOT_TOKEN')
youtube_api_key = os.getenv('YOUTUBE_API_KEY')

bot = Bot(token=bot_token)
dp = Dispatcher(bot)
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

app = FastAPI()

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{os.getenv('WEBHOOK_URL')}{WEBHOOK_PATH}"

async def search_youtube(query, max_results=4, page_token=None):
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

async def send_video_options(chat_id, query, videos, next_page_token):
    markup = InlineKeyboardMarkup()

    for index, video in enumerate(videos):
        button_text = f"{index + 1}. {video['title']}"
        video_button = InlineKeyboardButton(button_text, callback_data=video['video_id'])
        markup.add(video_button)

    if next_page_token:
        next_button = InlineKeyboardButton("Следующие 4 видео", callback_data=f"next_{next_page_token}_{query}")
        markup.add(next_button)

    for video in videos:
        await bot.send_photo(chat_id, video['thumbnail'], caption=video['title'])

    await bot.send_message(chat_id, "Выберите видео:", reply_markup=markup)

async def get_video_url(youtube_url):
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
        logger.error(f"Ошибка: {e}")
        return None

@dp.message_handler()
async def handle_message(message: types.Message):
    try:
        query = message.text
        logger.info(f"Получен запрос на поиск видео: {query}")
        videos, next_page_token = await search_youtube(query)
        logger.info(f"Найдено {len(videos)} видео по запросу: {query}")
        await send_video_options(message.chat.id, query, videos, next_page_token)
    except Exception as e:
        logger.error(f"Ошибка в обработке сообщения: {e}")

@dp.callback_query_handler()
async def callback_query(call: types.CallbackQuery):
    try:
        if call.data.startswith('next_'):
            _, next_page_token, query = call.data.split('_', 2)
            videos, next_page_token = await search_youtube(query, page_token=next_page_token)
            await send_video_options(call.message.chat.id, query, videos, next_page_token)
        else:
            video_id = call.data
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            video_url = await get_video_url(youtube_url)

            if video_url:
                await bot.send_message(call.message.chat.id, f"Видео найдено. Вот ссылка на видео: {video_url}")
            else:
                await bot.send_message(call.message.chat.id, "Не удалось получить видео. Попробуйте снова.")
    except Exception as e:
        logger.error(f"Ошибка в callback: {e}")
        await bot.send_message(call.message.chat.id, "Произошла ошибка при обработке запроса.")

@app.post(WEBHOOK_PATH)
async def process_webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Получен Webhook с данными: {data}")
        update = types.Update(**data)
        await dp.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Ошибка в Webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

@app.get("/")
async def index():
    return {"message": "Hello World"}


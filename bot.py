import os
import telebot
import yt_dlp
from googleapiclient.discovery import build
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')
youtube_api_key = os.getenv('YOUTUBE_API_KEY')

bot_token = '7553396600:AAHTwNczEj37Qx02KFADRSNpP_nrj0hySqs'
youtube_api_key = 'AIzaSyCDsHoy2T0pvbNzOo-hxEDxIMIeVAxqLOI'

bot = telebot.TeleBot(bot_token)
youtube = build('youtube', 'v3', developerKey=youtube_api_key)

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Введи запрос, и я найду видео на YouTube для тебя.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    query = message.text
    videos, next_page_token = search_youtube(query)
    send_video_options(message.chat.id, query, videos, next_page_token)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith('next_'):
        _, next_page_token, query = call.data.split('_', 2) 
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

def start_bot():
    bot.delete_webhook()
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)


if __name__ == '__main__':
    start_bot()


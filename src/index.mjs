import express from 'express';
import bodyParser from 'body-parser';
import axios from 'axios';
import dotenv from 'dotenv';
import ytDlp from 'yt-dlp';

dotenv.config();
const app = express();
const botToken = process.env.BOT_TOKEN;
const youtubeApiKey = process.env.YOUTUBE_API_KEY;

app.use(bodyParser.json());

async function searchYoutube(query, maxResults = 4, pageToken = null) {
    const response = await axios.get(`https://www.googleapis.com/youtube/v3/search`, {
        params: {
            part: 'snippet',
            q: query,
            type: 'video',
            maxResults: maxResults,
            pageToken: pageToken,
            key: youtubeApiKey,
        },
    });

    const videos = response.data.items.map(item => ({
        title: item.snippet.title,
        videoId: item.id.videoId,
        thumbnail: item.snippet.thumbnails.high.url,
    }));

    const nextPageToken = response.data.nextPageToken || null;
    return { videos, nextPageToken };
}

async function getVideoUrl(youtubeUrl) {
    try {
        const ydl = new ytDlp.YoutubeDL();
        const info = await ydl.extractInfo(youtubeUrl);
        return info.url;
    } catch (error) {
        console.error('Ошибка при получении URL:', error);
        return null;
    }
}

app.post(`/webhook`, async (req, res) => {
    const { message, callback_query } = req.body;

    if (message) {
        const query = message.text;
        const { videos, nextPageToken } = await searchYoutube(query);
        sendVideoOptions(message.chat.id, videos, nextPageToken);
    }

    if (callback_query) {
        const videoId = callback_query.data;
        const youtubeUrl = `https://www.youtube.com/watch?v=${videoId}`;
        const videoUrl = await getVideoUrl(youtubeUrl);

        if (videoUrl) {
            await sendMessage(callback_query.message.chat.id, `Видео найдено: ${videoUrl}`);
        } else {
            await sendMessage(callback_query.message.chat.id, 'Не удалось получить видео. Попробуйте снова.');
        }
    }

    res.send('OK');
});

async function sendMessage(chatId, text) {
    await axios.post(`https://api.telegram.org/bot${botToken}/sendMessage`, {
        chat_id: chatId,
        text: text,
    });
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Сервер запущен на порту ${PORT}`);
});

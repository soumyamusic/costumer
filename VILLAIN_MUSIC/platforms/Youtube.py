import asyncio
import os
import re
import time
from typing import Union
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch
from VILLAIN_MUSIC.utils.formatters import time_to_seconds
import aiohttp
import random

# ---------- GLOBAL SESSION ----------
SESSION: aiohttp.ClientSession = None

async def get_session():
    global SESSION
    if SESSION is None or SESSION.closed:
        SESSION = aiohttp.ClientSession()
    return SESSION


def cookie_txt_file():
    cookie_dir = f"{os.getcwd()}/cookies"
    if not os.path.exists(cookie_dir):
        return None
    cookies_files = [f for f in os.listdir(cookie_dir) if f.endswith(".txt")]
    if not cookies_files:
        return None
    return os.path.join(cookie_dir, random.choice(cookies_files))


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def stream_url(self, link: str, audio: bool = True):
        """
        Get direct streaming URL (no download).
        """
        ydl_opts = {
            "quiet": True,
            "format": "bestaudio[ext=m4a]/bestaudio" if audio else "best[height<=720][ext=mp4]",
        }
        cookie_file = cookie_txt_file()
        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            return info["url"], info

    async def download(self, link: str, video: bool = False):
        """
        Hybrid system:
        - First try direct stream (instant play)
        - If fails, fallback to download
        """
        try:
            stream_link, info = await self.stream_url(link, audio=not video)
            return stream_link, False  # False = not a local file, direct stream
        except Exception as e:
            print(f"[Stream Fallback] {e}")
            return await self._fallback_download(link, video)

    async def _fallback_download(self, link: str, video: bool):
        """
        Old download method (slow but reliable).
        """
        loop = asyncio.get_running_loop()

        def run_dl():
            ydl_opts = {
                "format": "bestaudio/best" if not video else "best[height<=720][ext=mp4]",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "quiet": True,
                "nocheckcertificate": True,
            }
            cookie_file = cookie_txt_file()
            if cookie_file:
                ydl_opts["cookiefile"] = cookie_file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(link, download=True)
                return os.path.join("downloads", f"{info['id']}.{info['ext']}")

        path = await loop.run_in_executor(None, run_dl)
        return path, True  # True = local file

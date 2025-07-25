import requests
from bs4 import BeautifulSoup
from readability import Document
import re
import subprocess
import json as pyjson

YOUTUBE_REGEX = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/')


def fetch_youtube_metadata(url):
    """
    Use yt-dlp to fetch YouTube video metadata as a dict.
    """
    try:
        result = subprocess.run([
            'yt-dlp', '--dump-json', '--no-warnings', url
        ], capture_output=True, text=True, check=True)
        data = pyjson.loads(result.stdout)
        return {
            'url': url,
            'type': 'video',
            'title': data.get('title'),
            'description': data.get('description'),
            'channel': data.get('channel'),
            'upload_date': data.get('upload_date'),
            'duration': data.get('duration'),
            'metadata': data
        }
    except Exception as e:
        return {'url': url, 'type': 'video', 'error': str(e)}


def fetch_article_content(url):
    """
    Fetch and extract main text from a web page using readability-lxml.
    Fallback to BeautifulSoup for title/meta if needed.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        doc = Document(resp.text)
        title = doc.short_title()
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, 'html.parser')
        text = soup.get_text(separator='\n', strip=True)
        return {
            'url': url,
            'type': 'article',
            'title': title,
            'text': text
        }
    except Exception as e:
        # Fallback: just get title/meta
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.title.string if soup.title else ''
            desc = ''
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                desc = desc_tag.get('content', '')
            return {
                'url': url,
                'type': 'unknown',
                'title': title,
                'text': desc,
                'error': str(e)
            }
        except Exception as e2:
            return {'url': url, 'type': 'unknown', 'error': f'{e}; {e2}'}


def fetch_and_extract(url):
    """
    Dispatcher: Detect content type and call the appropriate extractor.
    Returns a dict with url, type, title, text/description, and extra metadata.
    """
    if YOUTUBE_REGEX.match(url):
        return fetch_youtube_metadata(url)
    # TODO: Add more video/PDF detection here
    return fetch_article_content(url) 
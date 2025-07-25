import requests
from bs4 import BeautifulSoup
from readability import Document
import re
import subprocess
import json as pyjson
from urllib.parse import urlparse
import shlex

YOUTUBE_REGEX = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/')


def validate_url(url):
    """
    Validate and sanitize URL to prevent command injection.
    Returns True if URL is safe, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False
    
    # Check for shell metacharacters that could be used for command injection
    dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '{', '}', '[', ']', '<', '>', '"', "'", '\\']
    if any(char in url for char in dangerous_chars):
        return False
    
    # Validate URL format
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        if parsed.scheme not in ['http', 'https']:
            return False
        return True
    except Exception:
        return False


def fetch_youtube_metadata(url):
    """
    Use yt-dlp to fetch YouTube video metadata as a dict.
    """
    # Validate URL before processing
    if not validate_url(url):
        return {'url': url, 'type': 'video', 'error': 'Invalid or unsafe URL'}
    
    try:
        # Use shlex.quote to properly escape the URL for shell safety
        # Even though we're using a list, this provides additional safety
        safe_url = shlex.quote(url)
        
        result = subprocess.run([
            'yt-dlp', '--dump-json', '--no-warnings', url
        ], capture_output=True, text=True, check=True, timeout=30)
        
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
    except subprocess.TimeoutExpired:
        return {'url': url, 'type': 'video', 'error': 'Request timeout'}
    except TimeoutError:
        return {'url': url, 'type': 'video', 'error': 'Request timeout'}
    except subprocess.CalledProcessError as e:
        return {'url': url, 'type': 'video', 'error': f'yt-dlp error: {e.stderr}'}
    except Exception as e:
        return {'url': url, 'type': 'video', 'error': str(e)}


def fetch_article_content(url):
    """
    Fetch and extract main text from a web page using readability-lxml.
    Fallback to BeautifulSoup for title/meta if needed.
    """
    # Validate URL before processing
    if not validate_url(url):
        return {'url': url, 'type': 'article', 'error': 'Invalid or unsafe URL'}
    
    try:
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'HistoryHounder/1.0 (https://github.com/pkmishra/HistoryHound)'
        })
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
            resp = requests.get(url, timeout=10, headers={
                'User-Agent': 'HistoryHounder/1.0 (https://github.com/pkmishra/HistoryHound)'
            })
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
    # Validate URL before any processing
    if not validate_url(url):
        return {'url': url, 'type': 'unknown', 'error': 'Invalid or unsafe URL'}
    
    if YOUTUBE_REGEX.match(url):
        return fetch_youtube_metadata(url)
    # TODO: Add more video/PDF detection here
    return fetch_article_content(url) 
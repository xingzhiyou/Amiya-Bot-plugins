import os
import re
import aiohttp

from amiyabot import Message, Chain
from core import AmiyaBotPluginInstance

curr_dir = os.path.dirname(__file__)


# Image URL cache: url -> (text, image_url_or_path)
_url_cache: dict[str, tuple[str, str | None]] = {}
_cache_timeout = 300  # 5 minutes cache


def _is_image_by_content(data: bytes) -> bool:
    """Detect if content is an image by magic bytes."""
    if len(data) < 4:
        return False
    # PNG, JPEG, GIF, WebP magic bytes
    signatures = [
        (b'\x89PNG\r\n\x1a\n', '.png'),
        (b'\xff\xd8\xff', '.jpg'),
        (b'GIF87a', '.gif'),
        (b'GIF89a', '.gif'),
        (b'RIFF', '.webp'),  # WebP starts with RIFF....WEBP
    ]
    for sig, _ in signatures:
        if data.startswith(sig):
            return True
    return False


def _is_image_by_url(url: str) -> tuple[bool, str]:
    """Detect if URL likely points to an image by extension."""
    image_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico'}
    lower = url.lower()
    for ext in image_exts:
        if lower.endswith(ext) or ('?' in lower and lower.split('?')[0].endswith(ext)):
            return True, ext
    return False, ''


async def fetch_url_content(url: str) -> tuple[str, str | None]:
    """Fetch content from a URL with intelligent detection.
    
    Returns:
        tuple: (text content, image URL/path if it's an image, else None)
    """
    import time
    
    # Check cache
    if url in _url_cache:
        cached_text, cached_img = _url_cache[url]
        return cached_text, cached_img
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content_type = response.headers.get('Content-Type', '')
                    data = await response.read()
                    
                    is_image = False
                    ext = ''
                    
                    # Check by Content-Type header
                    if 'image' in content_type:
                        is_image = True
                        if 'png' in content_type:
                            ext = '.png'
                        elif 'gif' in content_type:
                            ext = '.gif'
                        elif 'webp' in content_type:
                            ext = '.webp'
                        else:
                            ext = '.jpg'
                    
                    # Check by URL extension
                    if not is_image:
                        is_image, ext = _is_image_by_url(url)
                    
                    # Check by content magic bytes
                    if not is_image:
                        is_image, ext = _is_image_by_content(data), ext or '.jpg'
                    
                    if is_image:
                        # Prefer returning URL directly if server supports it
                        if 'image' in content_type or _is_image_by_url(url)[0]:
                            _url_cache[url] = ('', url)
                            return '', url
                        
                        # Save to temp file
                        img_path = f'/tmp/url_image_{abs(hash(url))}{ext}'
                        if not os.path.exists(img_path):
                            with open(img_path, 'wb') as f:
                                f.write(data)
                        _url_cache[url] = ('', img_path)
                        return '', img_path
                    
                    # Return text content
                    text = data.decode('utf-8', errors='ignore')
                    _url_cache[url] = (text, None)
                    return text, None
                    
    except Exception:
        pass
    
    _url_cache[url] = ('', None)
    return '', None


async def parse_reply_content(reply: str, data: Message) -> tuple[str, str | None]:
    """Parse reply content, handling URL expressions and nickname placeholder.
    
    Returns:
        tuple: (text content, image path if there's an image, else None)
    """
    image_path = None
    
    # Handle URL expression: {url:https://example.com}
    url_pattern = r'\{url:([^}]+)\}'
    
    for match in re.finditer(url_pattern, reply):
        url = match.group(1)
        content, img_path = await fetch_url_content(url)
        if img_path:
            image_path = img_path
            reply = reply.replace(match.group(0), '')
        elif content:
            reply = reply.replace(match.group(0), content)
    
    # Replace nickname placeholder
    return reply.replace('{nickname}', data.nickname), image_path


class TalkPluginInstance(AmiyaBotPluginInstance): ...


bot = TalkPluginInstance(
    name='自定义回复',
    version='1.7',
    plugin_id='amiyabot-talking',
    plugin_type='official',
    description='可以自定义一问一答的简单对话',
    document=f'{curr_dir}/README.md',
    instruction=f'{curr_dir}/README_USE.md',
    global_config_schema=f'{curr_dir}/config_schema.json',
    global_config_default=f'{curr_dir}/config_default.yaml',
)


async def check_talk(data: Message):
    configs: list = bot.get_config('configs')

    def set_reply(_item):
        return True, 1, [_item['reply'], _item['is_at']]

    for item in configs:
        direct = item.get('direct')
        if direct:
            if direct == '仅群聊' and data.is_direct:
                continue
            if direct == '仅私聊' and not data.is_direct:
                continue

        if item['keyword_type'] == '包含关键词':
            if item['keyword'] in data.text:
                return set_reply(item)
        if item['keyword_type'] == '等于关键词':
            if item['keyword'] == data.text:
                return set_reply(item)
        if item['keyword_type'] == '正则匹配':
            if re.search(re.compile(item['keyword']), data.text):
                return set_reply(item)


@bot.on_message(verify=check_talk, check_prefix=False, allow_direct=True)
async def _(data: Message):
    reply: str = data.verify.keypoint[0]
    is_at: bool = data.verify.keypoint[1]

    if os.path.exists(reply):
        return Chain(data, at=is_at).image(reply)

    reply, image_path = await parse_reply_content(reply, data)
    
    chain = Chain(data, at=is_at)
    if image_path:
        chain = chain.image(image_path)
    if reply.strip():
        chain = chain.text(reply)
    
    return chain

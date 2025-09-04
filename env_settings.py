from collections.abc import Iterable
import os
from pathlib import Path

current_file = Path(__file__).resolve()
PROJECT_ROOT = current_file.parent


# Save Path
ATTACHMENT_FOLD = PROJECT_ROOT / 'atacchments'
CHAT_FOLD = PROJECT_ROOT / 'chat_history'
SERVER_INFO_FILE_PATH = PROJECT_ROOT / 'server_info.json'
CHANNEL_TYPE : Iterable|str|None = {'text', 'news_thread', 'public_thread', 'private_thread'} # 篩選想要儲存的頻道類型
CHROMA_CLIENT_PATH = PROJECT_ROOT / 'rag/chroma'
DEFAULT_COLLECTION_NAME = 'dc_chat'

ROLE_PROMPT_PATH = None

# 可調
GUILD_IDS : Iterable|int|str|None = None  # 輸入指定的伺服器 ID(s)，只會收集這些伺服器的頻道，None 為全部
MESSAGES_LIMIT = 3000


LLM_MODELS=[
    {'api_key' : 'your_key',
     'api_url' : "your_url", 
     'model_name' : "your_model"},

]

MLM_MODELS=[
    {'api_key' : 'your_key',
     'api_url' : "your_url", 
     'model_name' : "your_model"},

]

EMBEDDING_MODELS=[
    {'api_key' : 'your_key',
     'api_url' : "your_url", 
     'model_name' : "your_model"},

]

GEMINI_API_KEY = 'your_key'
GOOGLE_API_URL = "your_url"
EMBEDDING_MODEL = "your_model"
EMBEDDING_DIMENSION = 1536
EMBEDDING_RPM = 100



def get_discord_token():
    t = os.environ.get('DISCORD_BOT_TOKEN')
    if t is not None: return t
    else : raise ValueError("DISCORD_BOT_TOKEN 環境變量未設置")

DISCORD_BOT_TOKEN = get_discord_token()
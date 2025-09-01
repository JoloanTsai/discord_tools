from collections.abc import Iterable
import os

# Save Path
ATTACHMENT_FOLD = 'atacchments'
CHAT_FOLD = 'chat_history'
SERVER_INFO_FILE_PATH = 'server_info.json'
CHANNEL_TYPE : Iterable|str|None = {'text', 'news_thread', 'public_thread', 'private_thread'} # 篩選想要儲存的頻道類型

# 可調
GUILD_IDS : Iterable|int|str|None = 1216378539947851786  # 輸入指定的伺服器 ID(s)，只會收集這些伺服器的頻道，None 為全部
MESSAGES_LIMIT = 30




def get_discord_token():
    t = os.environ.get('DISCORD_BOT_TOKEN')
    if t is not None: return t
    else : raise ValueError("DISCORD_BOT_TOKEN 環境變量未設置")

DISCORD_BOT_TOKEN = get_discord_token()

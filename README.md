# Discord Bot Tools

利用 Discord 機器人來實現的一些功能

## 環境配置

**python 版本須 >= 3.10**

### 套件安裝
會使用到 graphrag, discord，使用 pip 安裝：
``` bash
pip install -r requirements.txt
```

### Discord Bot Token 設置
### 修改配置文件
需要先將你的 Discord Bot Token 設置到環境變數中：
```bash
export DISCORD_BOT_TOKEN=<your_token>
```
或是直接輸入到 `env_settings.py` 內（詳見樓下修改配置文件）

<br>

到 `env_settings.py` 中修改參數，填入 LLM, Embedding 模型的 API 資訊:

必填：
```python
LLM_MODELS=[
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
```

Option:
```python
# Save Path
ATTACHMENT_FOLD = 'atacchments'
CHAT_FOLD = 'chat_history'
SERVER_INFO_FILE_PATH = 'server_info.json'
CHANNEL_TYPE : Iterable|str|None = 'text' # 篩選想要儲存的頻道類型

# 可調
GUILD_IDS : Iterable|int|str|None = None  # 輸入指定的伺服器 ID(s)，只會收集這些伺服器的頻道，None 為全部
MESSAGES_LIMIT = 3000
```



<br>

## 使用伺服器機器人
`DISCORD_BOT_TOKEN` 環境變數設定好後，在終端機輸入：
``` bash
python main.py
```
就可以啟動 Discord 機器人，將機器人加進想要執行功能的伺服器中

<br>

### day_summary : 
在機器人有權限的頻道內輸入 `/ day_summary`，AI會總結當天的訊息

<br>





### 儲存文字頻道訊息

run:
```bash
python save_caht.py
```
這會將文字頻道內訊息儲存為 JSONL 檔，附件存於 `ATTACHMENT_FOLD` 路徑

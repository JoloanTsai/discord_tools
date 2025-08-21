'''
開機時check chat_history/tem_num.json 有沒有存在
last_id, last_message_id

考慮改用JSONL存聊天記錄
'''

import discord
import json, os
import asyncio
from discord.ext import commands
from env_settings import *
from get_chat_history import TextChannelInfo, get_channel_ids
intents = discord.Intents.default()
intents.guilds = True  # 啟用伺服器 Intent



def bot_init():
    # check chat_history/tem_num.json 有沒有存在
    global tem_num
    save_fold = chat_history_save_path
    try :
        with open(os.path.join(save_fold, 'tem_num.json'), 'r') as json_file:
            tem_num = json.load(json_file)
    except FileNotFoundError:
        os.makedirs(save_fold, exist_ok=True)
        with open(os.path.join(save_fold, 'tem_num.json'), 'w') as json_file:
            json_file.write("{}")
        tem_num = {}

def save_tem_num():
    with open(os.path.join(chat_history_save_path, 'tem_num.json'), "w") as json_file:
        j_data = json.dumps(tem_num, indent=2, ensure_ascii=False)
        json_file.write(j_data)

def get_last_id_from_tem(channel_id):
    try:
        last_id = tem_num[str(channel_id)]['last_id']
    except KeyError:
        last_id = 0
    
    return last_id

def get_last_message_id_from_tem(channel_id):
    try:
        last_message_id = tem_num[str(channel_id)]['last_message_id']
    except KeyError:
        last_message_id = None
    
    return last_message_id

async def get_channels_info_and_save(client):
    server_dict = {}
    
    # 遍歷機器人所在的每個伺服器
    for guild in client.guilds:
        guild_dict = {'guild_name': guild.name, 'guild_id': guild.id, 'channels' : []}

        print(f"--- 伺服器: {guild.name} (ID: {guild.id}) ---")
        
        # 遍歷伺服器內的所有頻道
        for channel in guild.channels:

            category_name = channel.category.name if channel.category else None
            category_id = channel.category.id if channel.category else None
            
            ch_dict = {'channel_name' : channel.name, 
                    'channel_id' : channel.id, 
                    'channel_type' : str(channel.type), 
                    'category_name': category_name,
                    'category_id': category_id}
            
            guild_dict['channels'].append(ch_dict)

            print(f"頻道名稱: {channel.name} | ID: {channel.id} | 類型: {channel.type}")

        server_dict[guild.id] = guild_dict
    
    # print(server_dict)    
    j_data = json.dumps(server_dict, indent=2, ensure_ascii=False)
    print("tes")
    with open(server_info_file_path, "w") as json_file:
        json_file.write(j_data)

client = commands.Bot(command_prefix = "$", intents = intents)

attachment_fold = ATTACHMENT_FOLD
chat_history_save_path = CHAT_FOLD
server_info_file_path = SERVER_INFO_FILE_PATH



tem_num = {}



bot_init()

@client.event
async def on_ready():
    print(f'登入身分: {client.user}')

    print('Collecting server data ...')
    await get_channels_info_and_save(client)
    print('Complete collecting!')

    
    try : 
        with open(server_info_file_path, 'r') as f:
            server_info_json = json.load(f)
    except FileNotFoundError : server_info_json = None

    chs = get_channel_ids(server_info_json, GUILDS, CHANNEL_TYPE)

    workers = [TextChannelInfo(client.get_channel(ch), get_last_id_from_tem(ch), get_last_message_id_from_tem(ch)) for ch in chs]
    print('正在檢查更新並搜集', str(len(workers)), '個頻道的對話...')
    tasks = [w.get_messages_and_latest_id_message_id() for w in workers]
    results = await asyncio.gather(*tasks)

    for ((g_id, ch_id), messages, latest_id, lastest_message_id) in results:
        chat_save_fold = os.path.join(chat_history_save_path, str(g_id))
        TextChannelInfo.save_jsonl(messages, chat_save_fold, str(ch_id) + '.jsonl')

        d = tem_num.setdefault(str(ch_id), {})
        d['last_id'] = latest_id
        d['last_message_id'] = lastest_message_id
    save_tem_num()
    
    await client.close()


client.run(DISCORD_BOT_TOKEN)


import discord
import json, os
import asyncio
from discord.ext import commands
from env_settings import *
from get_chat_history import TextChannelInfo, get_channel_ids, get_tum_num
intents = discord.Intents.default()
intents.guilds = True  # 啟用伺服器 Intent



def save_tem_num(tem_num:dict, chat_history_save_path = CHAT_FOLD):
    with open(os.path.join(chat_history_save_path, 'tem_num.json'), "w") as json_file:
        j_data = json.dumps(tem_num, indent=2, ensure_ascii=False)
        json_file.write(j_data)

def get_last_id_from_tem(tem_num:dict, channel_id):
    channel_data = tem_num.get(str(channel_id), {})
    last_id = channel_data.get('last_id', 0)
    
    return last_id

def get_last_message_id_from_tem(tem_num:dict, channel_id):
    try:
        last_message_id = tem_num[str(channel_id)]['last_message_id']
    except KeyError:
        last_message_id = None
    
    return last_message_id

def get_server_info_json(server_info_json=SERVER_INFO_FILE_PATH) -> dict:
    try : 
        with open(server_info_file_path, 'r') as f:
            server_info_json = json.load(f)
    except FileNotFoundError : server_info_json = {}

    return server_info_json


async def get_channels_info_and_save(client, select_guild_ids:list[int]|None = None, 
                                     server_info_file_path = SERVER_INFO_FILE_PATH,
                                     ignore_ch:set[int]|None=None):
    print('Collecting server data ...')
    server_info_json = get_server_info_json()
    if not select_guild_ids:
        guilds = client.guilds
    else :
        guilds = [client.get_guild(g_id) for g_id in select_guild_ids]
    # 遍歷機器人所在的每個伺服器
    for guild in guilds:
        guild_dict = {'guild_name': guild.name, 'guild_id': guild.id, 'channels' : {}}

        print(f"--- 伺服器: {guild.name} (ID: {guild.id}) ---")
        
        # 遍歷伺服器內的所有頻道
        for channel in guild.channels:
            if ignore_ch and (channel.id in ignore_ch):continue #跳過 ignore_ch

            category_name = channel.category.name if channel.category else None
            category_id = channel.category.id if channel.category else None
            
            ch_dict = {'channel_name' : channel.name, 
                    'channel_id' : channel.id, 
                    'channel_type' : str(channel.type), 
                    'category_name': category_name,
                    'category_id': category_id}
            
            guild_dict['channels'][str(channel.id)]=ch_dict

            print(f"頻道名稱: {channel.name} | ID: {channel.id} | 類型: {channel.type}")

            if isinstance(channel, discord.TextChannel):
                threads = channel.threads
                for thread in threads:
                    if ignore_ch and (thread.id in ignore_ch):continue #跳過 ignore_ch
                    thread_dict = {'channel_name' : thread.name, 
                            'channel_id' : thread.id, 
                            'channel_type' : str(thread.type), 
                            'category_name': channel.name,
                            'category_id': channel.id}
                    guild_dict['channels'][str(thread.id)]=thread_dict 

                    print(f"    thread: {thread.name} (ID: {thread.id})")

        server_info_json[str(guild.id)] = guild_dict
    
    j_data = json.dumps(server_info_json, indent=2, ensure_ascii=False)
    with open(server_info_file_path, "w") as json_file:
        json_file.write(j_data)
    
    print('Complete collecting!')

async def save_chat(client, guild_ids = GUILD_IDS, print_output_info=True, 
                    ignore_ch:set[int]|None=None):
    tem_num = get_tum_num()

    try : 
        with open(server_info_file_path, 'r') as f:
            server_info_json = json.load(f)
    except FileNotFoundError : server_info_json = None

    chs = get_channel_ids(server_info_json, guild_ids, CHANNEL_TYPE)
    # print('\n\n\nwowowow', chs, '\n\n\n')
    if ignore_ch:
        chs = set(chs) - ignore_ch
        print('\n\n\n', chs, '\n\n\n')

    workers = [TextChannelInfo(client.get_channel(ch), 
                               get_last_id_from_tem(tem_num, ch), 
                               get_last_message_id_from_tem(tem_num, ch),
                               client.user) for ch in chs]
    print('正在檢查更新並搜集', str(len(workers)), '個頻道的對話...')
    tasks = [w.get_messages_and_latest_id_message_id() for w in workers]
    results = await asyncio.gather(*tasks)

    log_dict = {}

    for ((g_id, ch_id), messages, latest_id, lastest_message_id) in results:
        chat_save_fold = os.path.join(chat_history_save_path, str(g_id))
        TextChannelInfo.save_jsonl(messages, chat_save_fold, str(ch_id) + '.jsonl')


        # 處理終端輸出
        if print_output_info:
            channel_name = None
            channel_name = server_info_json[str(g_id)]['channels'][str(ch_id)]['channel_name']

            ld = log_dict.setdefault(g_id, {})
            ld[ch_id] = {
                'channel_name':channel_name,
                # 'guild_name':server_info_json[str(g_id)]['guild_name'],
                'how_many_new_message':latest_id - get_last_id_from_tem(tem_num, ch_id)
            }



        # update tem_num.json
        d = tem_num.setdefault(str(ch_id), {})
        d['last_id'] = latest_id
        d['last_message_id'] = lastest_message_id
        d['guild_id'] = g_id


    # for coro in asyncio.as_completed(tasks):
    #     ((g_id, ch_id), messages, latest_id, lastest_message_id) = await coro
    #     chat_save_fold = os.path.join(chat_history_save_path, str(g_id))
    #     TextChannelInfo.save_jsonl(messages, chat_save_fold, str(ch_id) + '.jsonl')

    #     d = tem_num.setdefault(str(ch_id), {})
    #     d['last_id'] = latest_id
    #     d['last_message_id'] = lastest_message_id


    # for guild_id in server_info_json:
    #     guild_name = server_info_json[str(guild_id)]['guild_name']

    #     channels = server_info_json[str(guild_id)]['channels']
    #     for channel in channels:
    #         channel_name = channel['channel_name']

    if print_output_info:
        terminal_output = ""
        for g_id in log_dict:
            terminal_output += f"\n{server_info_json[str(g_id)]['guild_name']}:\n------------------------------------------\n"
            for ch_id in log_dict[g_id]:
                terminal_output += f"   {str(log_dict[g_id][ch_id]['channel_name'])}: 頻道中有 {str(log_dict[g_id][ch_id]['how_many_new_message'])} 則新訊息 \n"

        print(terminal_output)

    save_tem_num(tem_num)
    print("資料已儲存.")

client = commands.Bot(command_prefix = "$", intents = intents)

attachment_fold = ATTACHMENT_FOLD
chat_history_save_path = CHAT_FOLD
server_info_file_path = SERVER_INFO_FILE_PATH





import time

@client.event
async def on_ready():
    print(f'登入身分: {client.user}')

    await get_channels_info_and_save(client)
    await save_chat(client)
    
    await client.close()

if __name__ == '__main__':
    start = time.time()
    client.run(DISCORD_BOT_TOKEN)
    print(f"excute time : {str(time.time() - start)} s")


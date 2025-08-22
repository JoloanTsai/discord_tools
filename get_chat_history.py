import discord
import json, os
import asyncio
from os import makedirs
from env_settings import *
from collections.abc import Iterable


class TextChannelInfo():
    '''
    
    '''
    def __init__(self, text_channel, last_id, last_message_id, 
                 attachment_fold = ATTACHMENT_FOLD, 
                 chat_history_save_path = CHAT_FOLD):
        '''
        channel : 使用discord.Client.get_channel()的到的channel資訊
        last_id : 之前對話紀錄JSONL的最後一筆id
        last_message_id : 對話紀錄JSONL的最後一筆對話的 message_id
        attachment_save_path : 附件的儲存路徑
        '''
        if not isinstance(text_channel, discord.TextChannel):
            raise NotTextChannelError("Channel 的輸入必須是TextChannel!!!")

        self.channel = text_channel
        self.last_id = last_id
        self.last_message_id = last_message_id
        self.guild_id = text_channel.guild.id
        self.channel_id = text_channel.id
        self.attachment_save_path = os.path.join(attachment_fold, str(self.guild_id), str(self.channel_id))
        self.chat_save_fold = os.path.join(chat_history_save_path, str(self.guild_id))


    async def get_messages_and_latest_id_message_id(self) -> tuple[tuple[int, int], list, int, int]:
        '''
        輸出：(guild_id, channel_id), messages, latest_id, lastest_message_id
        '''
        self.messages, self.latest_id, self.lastest_message_id = await self._get_chat_message()
        return (self.guild_id, self.channel_id), self.messages, self.latest_id, self.lastest_message_id

    # async def get_messages(self) -> dict:
    #     return self.messages
    
    async def get_latest_id_and_message_id(self) -> tuple[int, int]:
        return self.latest_id, self.lastest_message_id

    async def _get_chat_message(self) -> tuple[list, int, int]:
        '''
        
        '''
        # (messages, latest_id), lastest_message_id = await asyncio.gather(
        #     self.get_messages(self.channel, last_id = self.last_id, last_message_id = self.last_message_id, atacchment_save_path = self.attachment_save_path),
        #     self.get_lastest_message_id(self.channel)
        #         )
        
        messages, latest_id, lastest_message_id = await self.get_messages_and_latest_message_id(
            self.channel, last_id = self.last_id, last_message_id = self.last_message_id, 
            atacchment_save_path = self.attachment_save_path)
        return messages, latest_id, lastest_message_id

    async def extract_message_data(self, message:discord.Message, id, atacchment_save_path):
        attachment_urls = []
        for att in message.attachments:
            save_path = f"{atacchment_save_path}/{att.filename}"
            attachment_urls.append(save_path)

            # await att.save(save_path)
            try : await att.save(save_path)
            except FileNotFoundError:
                makedirs(atacchment_save_path, exist_ok=True)
                await att.save(save_path)

        message_data = {
                'id' : id,
                'message' : message.content,
                'message_id' : message.id,
                'attachment_urls' : attachment_urls,
                'author_id' : message.author.id,
                'author_name' : message.author.global_name,
                'mentions' : [{
                                "id": m.id,
                                "name": m.name,
                                "bot": m.bot,
                                # "nick": m.nick,
                                }
                                for m in message.mentions]  if message.mentions else None,
                'replied_message_id' : message.reference.message_id if message.reference else None,
            }

        return message_data
    
    async def get_messages_and_latest_message_id(self, channel, last_id, last_message_id, atacchment_save_path) -> tuple[list[dict], int, int]:
        messages = []
        id = last_id
        if last_message_id:
            async for msg in channel.history(limit= MESSAGES_LIMIT, after = discord.Object(id=last_message_id), oldest_first=True):
                id += 1
                message_data = await self.extract_message_data(msg, id, atacchment_save_path)
                messages.append(message_data)
                # print('e')

        else:
            async for msg in channel.history(limit= MESSAGES_LIMIT, oldest_first=True):
                id+=1
                message_data = await self.extract_message_data(msg, id, atacchment_save_path)
                messages.append(message_data)
                # print('a')

        latest_id = id
        # print(messages)
        if messages:
            latest_message_id = messages[-1]['message_id']
        else : latest_message_id = last_message_id
        # print(latest_id)
        return messages, latest_id, latest_message_id

    async def get_messages(self, channel, last_id, last_message_id, atacchment_save_path) -> list[dict]:
        messages = []
        id = last_id
        if last_message_id:
            async for msg in channel.history(limit= MESSAGES_LIMIT, after = discord.Object(id=last_message_id), oldest_first=True):
                id += 1
                message_data = await self.extract_message_data(msg, id, atacchment_save_path)
                messages.append(message_data)
                # print('e')

        else:
            async for msg in channel.history(limit= MESSAGES_LIMIT, oldest_first=True):
                id+=1
                message_data = await self.extract_message_data(msg, id, atacchment_save_path)
                messages.append(message_data)
                # print('a')

        latest_id = id
        return messages, latest_id
            
    async def get_lastest_message_id(self, channel):
        try:
            latest_msg = await anext(channel.history(limit=1))
            if latest_msg:
                last_message_id = latest_msg.id
            return last_message_id
        except StopAsyncIteration:
            return None # 頻道沒有訊息

    @staticmethod
    def save_jsonl(json_dict:list, save_fold:str, file_name:str):
        try:
            with open(os.path.join(save_fold, file_name), "a") as json_file:
                for j_dict in json_dict:
                    j_data = json.dumps(j_dict, ensure_ascii=False)
                    json_file.write(j_data + '\n')
        except FileNotFoundError:
            makedirs(save_fold, exist_ok=True)
            with open(os.path.join(save_fold, file_name), "a") as json_file:
                for j_dict in json_dict:
                    j_data = json.dumps(j_dict, ensure_ascii=False)
                    json_file.write(j_data + '\n')

    def _save_json(self, json_dict:dict|list, save_fold:str, file_name:str):
        j_data = json.dumps(json_dict, indent=2, ensure_ascii=False)
        try:
            with open(os.path.join(save_fold, file_name), "w") as json_file:
                json_file.write(j_data)
        except FileNotFoundError:
            makedirs(save_fold, exist_ok=True)
            with open(os.path.join(save_fold, file_name), "w") as json_file:
                json_file.write(j_data)


def get_channel_ids(server_info_json:dict, select_guilds:Iterable|int|str|None = None,
                         select_ch_type:Iterable|str|None = None) -> list[int]:
    '''
    從 server_info_json 拿取 Channel ids
    select_guilds : input guild(s) which you want get Channel ids
    select_ch_type : 指定想要頻道類型
    '''
    if select_guilds is not None :
        # 如果 select_guilds 本身是 iterable，但不是 str 就 -> set
        if isinstance(select_guilds, Iterable) and not isinstance(select_guilds, (str, bytes)):
            guild_ids = set(select_guilds)
        else : guild_ids = {select_guilds}

    
    else: guild_ids = [guild for guild in server_info_json]
        
    # print(type(guild_ids), guild_ids)

    channel_types = {type.name for type in discord.ChannelType} # 拿到頻道所有的channel_type
    if select_ch_type is not None: 
        if isinstance(select_ch_type, str): # turn select_ch_type to set
            select_ch_type = {select_ch_type}
        else :
            select_ch_type = set(select_ch_type)

        if not select_ch_type.issubset(channel_types) :
            raise ChannelTypeError(f"select_ch_type 的輸入必須是 discord 官方的 channel type ： \n {channel_types}")
        
        channel_ids = [ch['channel_id'] for guild in guild_ids
                                        for ch in server_info_json[str(guild)]['channels']
                                        if ch['channel_type'] in select_ch_type]
    else :
        # channel_ids = []
        # for guild in server_info_json:
        #     channel_ids_in_guild = [ch['channel_id'] for ch in server_info_json[guild]['channels']]
        #     channel_ids += channel_ids_in_guild
        channel_ids = [ch['channel_id'] for guild in guild_ids
                                        for ch in server_info_json[guild]['channels']]
        
    return channel_ids


class ChannelTypeError(Exception):
    pass

class NotTextChannelError(Exception):
    pass


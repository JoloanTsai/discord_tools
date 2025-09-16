'''
時區固定為 UTC+0
'''

import discord
import chromadb
from discord.ext import commands
import re
from env_settings import *
from ai_manager import LlmClient, LlmClientPool
from llm_response import get_today_messages_outputs_ch, get_today_messages_outputs_guild
from save_chat import save_chat, get_channels_info_and_save
from rag.rag_new_message import rag_new_message, rag_new_message_by_guild
from llm_response import ChromaGeminiClient
from datetime import datetime, timezone, timedelta

intents = discord.Intents.all()
intents.guilds = True  # 啟用伺服器 Intent
client = commands.Bot(command_prefix = "$", intents = intents)

def delete_rag_data_by_ch_id(chroma_client_path=CHROMA_CLIENT_PATH):

    pass


class ModalInputer(discord.ui.Modal, title = "text inputer"):
    def __init__(self, prompt: str, describtion: str):
        super().__init__()
        self.prompt = prompt
        self.describtion = describtion
        self.user_input = ""
        
        # 創建文字輸入欄位
        self.text_input = discord.ui.TextInput(
            label=self.prompt,
            placeholder=self.describtion,  # 預設提示文字
            required=True,  # 必須填寫
            max_length=1000  # 最大字數限制
        )
        
        # 將輸入欄位添加到 Modal
        self.add_item(self.text_input)

    # Modal 提交後接著要執行的程式碼
    async def on_submit(self, interaction: discord.Interaction):
        self.user_input = self.text_input.value
        await interaction.response.defer()

async def pool_ai_invoke(pool, message, keep_think = None) -> str:
    try:
        machine = await pool.acquire()
        result = await machine.invoke(message)

        # 像Qwen3 會將思考和輸出放在一起，只保留輸出移除思考內容
        if (not keep_think) and ("<think>" in result) and ("</think>" in result):
            # 使用正規表達式移除 <think> 和 </think> 標籤及其中的所有內容
            result = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)

        return result
    finally:
        await pool.release(machine)

llms = [LlmClient(x['model_name'], x['api_key'], x['api_url']) for x in LLM_MODELS]
llm_pool = LlmClientPool(llms)

with open(PROJECT_ROOT / 'prompts/summary.txt', 'r', encoding="utf-8") as f:
    summary_prompt = f.read()

with open(PROJECT_ROOT / 'prompts/rag_ans.txt', 'r', encoding="utf-8") as f:
    rag_ans_prompt = f.read()

try:
    with open(PROJECT_ROOT / 'target_channels.txt', 'r', encoding="utf-8") as file:
        content = file.read()
        target_channels:set = eval(content)
except FileNotFoundError:
    target_channels = set()
    with open(PROJECT_ROOT / 'target_channels.txt', 'w', encoding="utf-8") as file:
        file.write('{0,}')

def save_target_channels(target_channels:set):
    content = str(target_channels)
    with open(PROJECT_ROOT / 'target_channels.txt', 'w', encoding="utf-8") as file:
        file.write(content)


if ROLE_PROMPT_PATH :
    with open(ROLE_PROMPT_PATH, 'r', encoding="utf-8") as f:
        role_prompt = f.read()
else: role_prompt = ''




async def get_day_summary_text_ch(channel_id:str, guild_id:int):
    await get_channels_info_and_save(client, select_guild_ids=[guild_id], ignore_ch=target_channels)
    await save_chat(client, guild_ids=guild_id, print_output_info=False)

    input_text = get_today_messages_outputs_ch(channel_id)
    if input_text != "Today has no message.":
        messages = [
            {"role": "system", "content": f"{role_prompt}{summary_prompt}"},
            {
                "role": "user",
                "content": f"{input_text}",
            },
        ]
        output_text = await pool_ai_invoke(llm_pool, messages)

    else : output_text = input_text

    return output_text


async def get_day_summary_text_guild(guild_id:int):
    await get_channels_info_and_save(client, select_guild_ids=[guild_id], ignore_ch=target_channels)
    await save_chat(client, guild_ids=guild_id, print_output_info=False)

    input_text = get_today_messages_outputs_guild(guild_id=guild_id)
    if input_text != "Today has no message.":
        messages = [
            {"role": "system", "content": f"{role_prompt}{summary_prompt}"},
            {
                "role": "user",
                "content": f"{input_text}",
            },
        ]
        output_text = await pool_ai_invoke(llm_pool, messages)

    else : output_text = input_text

    return output_text


async def get_rag_query_text(input_text:str, guild_id:int, user_name:str):
    await get_channels_info_and_save(client, select_guild_ids=[guild_id], ignore_ch=target_channels)
    await save_chat(client, guild_ids=guild_id, print_output_info=False)
    await rag_new_message_by_guild(guild_id)

    # 拿到現在時間
    tz_offset = timezone(timedelta(hours=0)) 
    iso_string = datetime.now(tz_offset).isoformat()
    
    
    cc = ChromaGeminiClient()
    query_output = cc.query_rag_with_width(input_text, QUERT_N_RESULTS, QUERT_MSG_WIDTH, collection_name=str(guild_id), ignore_ch=target_channels)
    web_search = 'None'

    # print(query_output)

    messages = [
                {"role": "system", "content": f"{role_prompt}{rag_ans_prompt}"},
                {
                    "role": "user",
                    "content": f"query_output:{ {query_output} }.\n\n web_search:{ {web_search} }. \n\n，使用者({user_name})問的問題：{ {input_text} }.\n 現在時間：{iso_string}",
                },
            ]
    
    output_text = await pool_ai_invoke(llm_pool, messages)

    return output_text




@client.event
async def on_ready():
    print(f'登入身分: {client.user}')
    slash = await client.tree.sync()


@client.tree.command(name='start', description='開始在該頻道使用自動 AI 功能')
async def start_ai(interaction:discord.Interaction):
    guild_id:int = interaction.guild.id
    channel_id:int = interaction.channel.id
    target_channels.add(channel_id)
    save_target_channels(target_channels)

    cc = ChromaGeminiClient()
    try:
        cc.delete_rag_data_by_ch_id(guild_id, channel_id)
    except :pass

    await interaction.response.send_message('start!')

@client.tree.command(name='stop', description='停止在該頻道使用自動 AI 功能')
async def stop_ai(interaction:discord.Interaction):
    channel_id = interaction.channel.id
    target_channels.discard(channel_id)
    save_target_channels(target_channels)
    await interaction.response.send_message('stop!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id in target_channels:
        guild_id:int = message.guild.id
        input_text = message.content
        output_text = await get_rag_query_text(input_text, guild_id, message.author)
        # output_text = input_text
        await message.channel.send(output_text)





@client.tree.command(name='day_summary_channel', description='彙整該頻道一天的訊息')
async def day_summary_channel(interaction:discord.Interaction):
    channel_id = str(interaction.channel.id)  # 獲取訊息所在頻道的ID
    guild_id:int = interaction.guild.id
    output_text = await get_day_summary_text_ch(channel_id, guild_id)

    await interaction.response.send_message(output_text)

@client.tree.command(name='day_summary', description='彙整伺服器中所有頻道一天的訊息')
async def day_summary(interaction:discord.Interaction):
    guild_id:int = interaction.guild.id
    output_text = await get_day_summary_text_guild(guild_id)

    await interaction.response.send_message(output_text)

@client.tree.command(name='rag_query', description='從rag中提取資訊給大模型回答')
async def rag_query(interaction:discord.Interaction):
    guild_id:int = interaction.guild.id
    input_modal = ModalInputer(f'輸入你想問關於這個伺服器的任何事情', '')
    await interaction.response.send_modal(input_modal)
    await input_modal.wait()
    input_text = input_modal.user_input
    output_text = await get_rag_query_text(input_text, guild_id, interaction.user)

    await interaction.channel.send(output_text)


if __name__ == '__main__':
    client.run(DISCORD_BOT_TOKEN)
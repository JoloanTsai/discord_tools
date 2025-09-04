import discord
from discord.ext import commands
from env_settings import *
from get_chat_history import TextChannelInfo, get_channel_ids, get_tum_num
from ai_manager import LlmClient, LlmClientPool
from llm_response import get_today_messages_outputs
from save_chat import save_chat, get_channels_info_and_save

intents = discord.Intents.default()
intents.guilds = True  # 啟用伺服器 Intent
client = commands.Bot(command_prefix = "$", intents = intents)


async def pool_ai_invoke(pool, message) -> str:
    try:
        machine = await pool.acquire()
        return await machine.invoke(message)
    finally:
        pool.release(machine)

llms = [LlmClient(x['model_name'], x['api_key'], x['api_url']) for x in MLM_MODELS]
llm_pool = LlmClientPool(llms)

with open(PROJECT_ROOT / 'prompts/summary.txt') as f:
    summary_prompt = f.read()

if ROLE_PROMPT_PATH :
    with open(ROLE_PROMPT_PATH) as f:
        role_prompt = f.read()
else: role_prompt = ''


async def get_day_summary_text(channel_id:str):
    await get_channels_info_and_save(client)
    await save_chat(client, print_output_info=False)

    input_text = get_today_messages_outputs(channel_id)
    messages = [
        {"role": "system", "content": f"{role_prompt}{summary_prompt}"},
        {
            "role": "user",
            "content": f"{input_text}",
        },
    ]
    output_text = await pool_ai_invoke(llm_pool, messages)
    return output_text

@client.event
async def on_ready():
    print(f'登入身分: {client.user}')
    slash = await client.tree.sync()

@client.tree.command(name='start', description='開始使用')
async def start(interaction:discord.Interaction):
    #get channel ID
    channel_id = interaction.channel.id  # 獲取訊息所在頻道的ID
    print("got")
    await interaction.response.send_message('hello')

@client.tree.command(name='day_summary', description='彙整該頻道一天的訊息')
async def day_summary(interaction:discord.Interaction):
    channel_id = str(interaction.channel.id)  # 獲取訊息所在頻道的ID
    output_text = await get_day_summary_text(channel_id)

    await interaction.response.send_message(output_text)


if __name__ == '__main__':
    client.run(DISCORD_BOT_TOKEN)
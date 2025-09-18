'''
RAG後的訊息，取前後 10 則 （或依時間決定） -> llm
Web search
tts
summary ai
def get_range_message_by_msg_width


'''

import chromadb
import json
import asyncio
from collections import defaultdict
from openai import OpenAI, AsyncOpenAI
from env_settings import *
from chromadb.utils.embedding_functions import EmbeddingFunction, DefaultEmbeddingFunction
from itertools import islice
from datetime import datetime, timezone
from save_chat import get_tum_num
from get_chat_history import get_date_messages, get_channel_ids
from save_chat import get_server_info_json
from ai_manager import embedding_pool, EmbeddingClient
# from rag.config import custom_ef



class ChromaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, client, model_name, dimensions):
        self.client = client
        self.model_name = model_name
        self.dimensions = dimensions
    

    def __call__(self, texts):
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts,
            dimensions=self.dimensions
        )
        return [d.embedding for d in response.data]
    



class ChromaGeminiClient():
    def __init__(self, emb_client:EmbeddingClient, embedding_dim= EMBEDDING_DIMENSION,
                 chroma_client_path=CHROMA_CLIENT_PATH):
        
        self.emb_client = emb_client
        self.ef = ChromaEmbeddingFunction(self.emb_client.no_async_client, emb_client.model, embedding_dim)
        self.chroma_client = chromadb.PersistentClient(path=chroma_client_path)


    def query_rag(self, query_texts:str, n_results:int, collection_name:str = DEFAULT_COLLECTION_NAME) -> chromadb.QueryResult:
        collection = self._get_collection(collection_name)

        results = collection.query(
            query_texts=query_texts,
            n_results=n_results
        )
        
        return results
    
    async def query_rag_with_width(self, query_texts:str, n_results:int, msg_width=10, 
                             collection_name:str = DEFAULT_COLLECTION_NAME, 
                             ignore_ch:set[int]|None=None) -> str:
        collection = self._get_collection(collection_name)
        await self.emb_client.add_request(1)

        results = collection.query(
            query_texts=query_texts,
            n_results=n_results
        )
        
        return self.get_width_message(results, msg_width, ignore_ch)
    
    def delete_rag_data_by_ch_id(self, guild_id:int|str , channel_id:int|str):
        
        collection = self._get_collection(str(guild_id))

        ids = collection.get()["ids"]
        delete_ids = []
        for rag_id in ids:
            g_id, ch_id, id = rag_id.split('_')
            if ch_id == str(channel_id): delete_ids.append(rag_id)

        collection.delete(ids=delete_ids)

    @staticmethod
    def get_width_message(results:chromadb.QueryResult, msg_width=10, ignore_ch:set[int]|None=None) -> str:
        docs = results['documents'][0]
        ids = results['ids'][0]
        obj = [get_range_message_by_msg_width(rag_id, msg_width=msg_width, ignore_ch=ignore_ch) for rag_id in ids]
        
        if obj:
            contents = []
            for o, rag_id in zip(obj, ids):
                if o is None :continue 
                g_id, ch_id, id = rag_id.split('_')
                ch_id_save = g_id + '_' + ch_id + '_'

                conts = get_contents_str_by_messages(o, ch_id_save)
                contents += conts

            contents = list(set(contents)) # 去除list中重複的元素
            ids, docs = zip(*contents)
            output_text = reults_to_llm_input(ids, docs)

            return output_text

        else :
            return "Got no one message."

        
    
    def _get_collection(self, collection_name:str) -> chromadb.Collection:
        try:
            collection = self.chroma_client.get_collection(name=collection_name, embedding_function=self.ef)

        except chromadb.errors.NotFoundError:
            collection = self.chroma_client.create_collection(name=collection_name, embedding_function=self.ef)

        return collection


def get_range_message_by_msg_width(rag_id:str, msg_width:int = 10, ignore_ch:set[int]|None=None) -> list[dict]:
    '''
    拿到指定 message，並回傳前後 msg_width 個的訊息 
    '''
    g_id, ch_id, id = rag_id.split('_')
    target = int(id)
    if ignore_ch and (target in ignore_ch):
        return None
        
    else: 
        skip = target-msg_width if target >= msg_width else None
        stop = target+msg_width
        with open(f"{CHAT_FOLD}/{g_id}/{ch_id}.jsonl", "r", encoding="utf-8") as f:
            obj = [json.loads(line) for line in islice(f, skip, stop)]

        return obj

def reults_to_llm_input(ids:list[str], docs:list[str]) -> str:
    '''
    ids : [gid_chid_id,]
    docs : [messages,]
    '''
    try : 
        with open(SERVER_INFO_FILE_PATH, 'r', encoding="utf-8") as f:
            server_info_json = json.load(f)
    except FileNotFoundError : server_info_json = None

    bucket = defaultdict(list)
    for id, d in zip(ids, docs):
        g, ch, i = id.split('_')
        bucket[ch].append((g, ch, int(i), d))

    for ch in bucket:
        bucket[ch].sort(key=lambda x: x[2])          # 依 id 排序

    output_text = ''

    for ch in bucket:
        g_id = bucket[ch][0][0]
        ch_name = server_info_json[g_id]['channels'][ch]['channel_name']

        output_text += f"\n\n頻道:{ch_name}  對話:[ \n"
        for _, _, _, msg in bucket[ch]:
            output_text += f"({msg})\n"

        output_text+=']'
    return output_text


def get_today_messages_outputs_ch(ch_id:str, max_outputs:int=100):
    dc_tem = get_tum_num()
    g_id = str(dc_tem[ch_id]['guild_id'])
    ch_id_save = g_id+'_'+ch_id+'_'

    today = datetime.now(timezone.utc).date()
    obj = get_date_messages(ch_id, today, max_outputs=max_outputs)
    if obj:
        contents = get_contents_str_by_messages(obj, ch_id_save)
        ids, docs = zip(*contents)
        output_text = reults_to_llm_input(ids, docs)
    
        return output_text
    
    else:
        return "Today has no message."

def get_today_messages_outputs_guild(guild_id:str|int, max_outputs:int=100):
    output_text = ""
    g_id = str(guild_id)

    server_info_json = get_server_info_json()
    contents = []

    today = datetime.now(timezone.utc).date()
    chs = get_channel_ids(server_info_json, guild_id, CHANNEL_TYPE)
    for ch_id_int in chs:
        ch_id = str(ch_id_int)
        obj = get_date_messages(ch_id, today, max_outputs=max_outputs)
        if obj:
            ch_id_save = g_id+'_'+ch_id+'_'
            conts = get_contents_str_by_messages(obj, ch_id_save)
            contents += conts

    if contents:
        contents = list(set(contents)) # 去除list中重複的元素
        ids, docs = zip(*contents)
        output_text = reults_to_llm_input(ids, docs)
        
        return output_text
    else:
        return "Today has no message."



def get_contents_str_by_messages(messages:list, ch_id_save:str):
    '''
    ch_id_save = g_id + '_' + ch_id + '_'
    '''
    return [(f"{ch_id_save}{m['id']}", (
                    (f"message:{m['message']}," if m['message'] else "message: send a attachment,") 
                    + f" send from:{m['author_name']}, time:{m['date']}."
                    + (f"\nThis message is in reply to:{m['replied_message']}" if m['replied_message'] else "")
                ))
                        for m in messages]

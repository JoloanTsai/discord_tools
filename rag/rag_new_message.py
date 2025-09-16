import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
import chromadb
from openai import OpenAI
from env_settings import *
from ai_manager import EmbeddingClient, EmbeddingClientPool
from llm_response import get_contents_str_by_messages
from save_chat import get_server_info_json
from itertools import islice
from chromadb.utils.embedding_functions import EmbeddingFunction



def get_tum_num(tem_num_save_fold) -> dict:
    # check chat_history/tem_num.json 有沒有存在
    save_fold = tem_num_save_fold
    try :
        with open(os.path.join(save_fold, 'tem_num.json'), 'r', encoding="utf-8") as json_file:
            tem_num = json.load(json_file)
    except FileNotFoundError:
        os.makedirs(save_fold, exist_ok=True)
        with open(os.path.join(save_fold, 'tem_num.json'), 'w', encoding="utf-8") as json_file:
            json_file.write("{}")
        tem_num = {}

    return tem_num

def save_tem_num(tem_num:dict, tem_num_save_fold):
    with open(os.path.join(tem_num_save_fold, 'tem_num.json'), "w", encoding="utf-8") as json_file:
        j_data = json.dumps(tem_num, indent=2, ensure_ascii=False)
        json_file.write(j_data)

def get_last_id_from_tem(tem_num:dict, channel_id):
    channel_data = tem_num.get(str(channel_id), {})
    last_id = channel_data.get('last_id', 0)
    
    return last_id

def get_contents_from_chat() -> list[tuple[str, str]]:
    '''
    不分 guild，會全部拿出
    使用embedding 資料夾內的 tem_num.json 比較 chat_fold 內的 tem_num.json，
    查看哪些是還沒被加進向量資料庫的內容，輸出 contents，並更新 embedding/tem_num.json
    '''

    dc_tem = get_tum_num(CHAT_FOLD)
    emb_tem = get_tum_num(PROJECT_ROOT/"rag/embeddings")

    contents :list[tuple[str, str]] = []

    for ch_id in dc_tem:
        ch_id_save = str(dc_tem[ch_id]["guild_id"]) + '_'+ch_id+'_'


        if ch_id not in emb_tem:
            d = emb_tem.setdefault(ch_id, {})
            d['last_id'] = 0


        new_message = dc_tem[ch_id]['last_id'] - emb_tem[ch_id]['last_id']
        if new_message == 0 : continue

        skip = emb_tem[ch_id]['last_id']
        with open(f"{CHAT_FOLD}/{str(dc_tem[ch_id]['guild_id'])}/{ch_id}.jsonl", "r", encoding="utf-8") as f:
            obj = [json.loads(line) for line in islice(f, skip, None)]
            conts = get_contents_str_by_messages(obj, ch_id_save)
            # conts = [(f"{ch_id_save}{m['id']}", (
            #     (f"message:{m['message']}," if m['message'] else "message: send a attachment,") 
            #     + f" send from:{m['author_name']}, time:{m['date']}."
            #     + (f"\nThis message is in reply to:{m['replied_message']}" if m['replied_message'] else "")
            # ))
            #         for m in obj]
            
        contents += conts

        d = emb_tem.setdefault(ch_id, {})
        d['last_id'] = dc_tem[ch_id]['last_id']

    def save_emb_tem_num():
        save_tem_num(emb_tem, PROJECT_ROOT/"rag/embeddings")
    
    return contents, save_emb_tem_num

def get_contents_from_guild(guild_id:int, ignore_ch:set[int]|None=None) -> list[tuple[str, str]]:
    '''
    指定 guild
    使用embedding 資料夾內的 tem_num.json 比較 chat_fold 內的 tem_num.json，
    查看哪些是還沒被加進向量資料庫的內容，輸出 contents，並更新 embedding/tem_num.json
    '''

    dc_tem = get_tum_num(CHAT_FOLD)
    emb_tem = get_tum_num(PROJECT_ROOT/"rag/embeddings")
    g_id = str(guild_id)

    contents :list[tuple[str, str]] = []

    for ch_id in dc_tem:
        if (dc_tem[ch_id]['guild_id'] != guild_id) or (ignore_ch and int(ch_id) in ignore_ch) : continue # 如果不是指定的 guild_id 或是在 ignore_ch 內就跳過
        ch_id_save = g_id + '_'+ch_id+'_'

        if ch_id not in emb_tem:
            d = emb_tem.setdefault(ch_id, {})
            d['last_id'] = 0


        new_message = dc_tem[ch_id]['last_id'] - emb_tem[ch_id]['last_id']
        if new_message == 0 : continue

        skip = emb_tem[ch_id]['last_id']
        with open(f"{CHAT_FOLD}/{g_id}/{ch_id}.jsonl", "r", encoding="utf-8") as f:
            obj = [json.loads(line) for line in islice(f, skip, None)]
            conts = get_contents_str_by_messages(obj, ch_id_save)
            # conts = [(f"{ch_id_save}{m['id']}", (
            #     (f"message:{m['message']}," if m['message'] else "message: send a attachment,") 
            #     + f" send from:{m['author_name']}, time:{m['date']}."
            #     + (f"\nThis message is in reply to:{m['replied_message']}" if m['replied_message'] else "")
            # ))
            #         for m in obj]
            
        contents += conts

        d = emb_tem.setdefault(ch_id, {})
        d['last_id'] = dc_tem[ch_id]['last_id']

    def save_emb_tem_num():
        save_tem_num(emb_tem, PROJECT_ROOT/"rag/embeddings")
    
    return contents, save_emb_tem_num

async def batch_rag(pool: EmbeddingClientPool, task_queue: asyncio.Queue):
    """從任務隊列取任務，用空閒的客戶端處理"""
    results = []
    
    async def worker():
        while True:
            try:
                content = await task_queue.get()
                if content is None:  # 結束信號
                    break
                
                ids = [cont[0] for cont in content]
                docs = [cont[1] for cont in content]
                
                # 取得空閒客戶端
                client = await pool.acquire()
                
                try:
                    a = await client.get_id_doc_embedding(ids, docs)
                    results.extend(a)
                    
                finally:
                    await pool.release(client)
                    task_queue.task_done()
                    
            except Exception as e:
                print(f"處理錯誤: {e}")
    
    # 啟動工作協程
    workers = [asyncio.create_task(worker()) for _ in range(pool.worker_num)]  # 可調整工作者數量
    
    # 等待任務隊列清空
    await task_queue.join()
    
    # 發送結束信號
    for _ in workers:
        await task_queue.put(None)
    
    # 等待所有工作者結束
    await asyncio.gather(*workers)

    return results


# def embedding(client, ids, docs:list[str]) -> list[list]:
    # response =client.embeddings.create(
    #     input=docs,
    #     model=EMBEDDING_MODEL,
    #     dimensions=1536
    # )

#     return [(id_, doc_, emb_) for id_, doc_, emb_ in zip(ids, docs, [item.embedding for item in response.data])]

def cut_list_by_batch(contents_list:list[str, str], batch_size):
    '''
    將 contents 依照batch_size 的大小切，讓每個 Client 一次處理 batch_size 的量
    '''
    return [contents_list[i:i + batch_size] for i in range(0, len(contents_list), batch_size)]



client = OpenAI(
    api_key=GEMINI_API_KEY,
    base_url=GOOGLE_API_URL
)

class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, client, model_name="gemini-embedding-001", dimensions=1536):
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

gemini_ef = GeminiEmbeddingFunction(client, EMBEDDING_MODEL, EMBEDDING_DIMENSION)




def add_vectors_in_chroma(contents:list[tuple[str, str, list]], collection_name:str, embedding_function = None):
    '''
    將ids, documents, embeddings 加進 chroma 資料庫
    '''
    if contents:
        chroma_client = chromadb.PersistentClient(CHROMA_CLIENT_PATH)
        try:
            collection = chroma_client.get_collection(name=collection_name, embedding_function=embedding_function)
        except chromadb.errors.NotFoundError:
            collection = chroma_client.create_collection(name=collection_name, embedding_function=embedding_function)

            
        collection.upsert(
            ids=[cont[0] for cont in contents],
            documents=[cont[1] for cont in contents],
            embeddings=[cont[2] for cont in contents],
        )



async def rag_new_message():
    contents, save_emb_tem_num = get_contents_from_chat()

    if contents:
        print(f"正在處理 {len(contents)} 條新訊息...")
        batched_contents = cut_list_by_batch(contents, BATCH_SIZE)

        # for x in contents:
        #     e = embedding(client, x[0], x[1])
        #     print(e)
        #     time.sleep(2)

        
        q = asyncio.Queue()
        for x in batched_contents:
            q.put_nowait(x)


        workers = [EmbeddingClient(x['model_name'], x['api_key'], x['api_url'], x['rpm'], EMBEDDING_DIMENSION) for x in EMBEDDING_MODELS]
        pool = EmbeddingClientPool(workers)
        results:list[tuple[str, str, list]] = await batch_rag(pool, q) # list[tuple[id, doc, embedding]]

        add_vectors_in_chroma(results, DEFAULT_COLLECTION_NAME)
        save_emb_tem_num()
        print("RAG complete!")
    
    else : print("Has no more new data need to rag")

async def rag_new_message_by_guild(guild_id:int, ignore_ch:set[int]|None=None):
    '''
    只針對單一 guild 內的訊息去做 RAG
    '''
    contents, save_emb_tem_num = get_contents_from_guild(guild_id, ignore_ch)

    if contents:
        print(f"正在處理 {len(contents)} 條新訊息...")
        batched_contents = cut_list_by_batch(contents, BATCH_SIZE)

        # for x in contents:
        #     e = embedding(client, x[0], x[1])
        #     print(e)
        #     time.sleep(2)

        
        q = asyncio.Queue()
        for x in batched_contents:
            q.put_nowait(x)


        workers = [EmbeddingClient(x['model_name'], x['api_key'], x['api_url'], x['rpm'], EMBEDDING_DIMENSION) for x in EMBEDDING_MODELS]
        pool = EmbeddingClientPool(workers)
        results:list[tuple[str, str, list]] = await batch_rag(pool, q) # list[tuple[id, doc, embedding]]

        add_vectors_in_chroma(results, str(guild_id))
        save_emb_tem_num()
        print("RAG complete!")
    
    else : print("Has no more new data need to rag")

    
if __name__ == '__main__':
    import time

    start = time.time()
    asyncio.run(rag_new_message())
    print(f"excute time : {str(time.time() - start)} s")

    
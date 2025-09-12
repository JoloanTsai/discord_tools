'''
RAG後的訊息，取前後 10 則 （或依時間決定） -> llm
Web search
tts
summary ai
def get_range_message_by_msg_width


'''

import chromadb
import json
from collections import defaultdict
from openai import OpenAI
from env_settings import *
from chromadb.utils.embedding_functions import EmbeddingFunction, DefaultEmbeddingFunction
from itertools import islice
from datetime import datetime
from save_chat import get_tum_num
from get_chat_history import get_date_messages
# from rag.config import custom_ef



class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, client, model_name, dimensions=1536):
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
    def __init__(self, model_name=EMBEDDING_MODEL, api_key=GEMINI_API_KEY, 
                 api_url=GOOGLE_API_URL, embedding_dim= EMBEDDING_DIMENSION,
                 chroma_client_path=CHROMA_CLIENT_PATH):
        
        self.emb_client = OpenAI(
                    api_key=api_key,
                    base_url=api_url
                )
        self.gemini_ef = GeminiEmbeddingFunction(self.emb_client, model_name, embedding_dim)
        self.chroma_client = chromadb.PersistentClient(path=chroma_client_path)


    def query_rag(self, query_texts:str, n_results:int, collection_name:str = DEFAULT_COLLECTION_NAME) -> chromadb.QueryResult:
        collection = self._get_collection(collection_name)

        results = collection.query(
            query_texts=query_texts,
            n_results=n_results
        )
        
        return results
    
    def query_rag_with_width(self, query_texts:str, n_results:int, msg_width=10, 
                             collection_name:str = DEFAULT_COLLECTION_NAME, 
                             ignore_ch:set[int]|None=None) -> str:
        collection = self._get_collection(collection_name)

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
                # conts = [(f"{ch_id_save}{m['id']}", (
                #     (f"message:{m['message']}," if m['message'] else "message: send a attachment,") 
                #     + f" send from:{m['author_name']}, time:{m['date']}."
                #     + (f"\nThis message is in reply to:{m['replied_message']}" if m['replied_message'] else "")
                # ))
                #         for m in o]

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
            collection = self.chroma_client.get_collection(name=collection_name, embedding_function=self.gemini_ef)

        except chromadb.errors.NotFoundError:
            collection = self.chroma_client.create_collection(name=collection_name, embedding_function=self.gemini_ef)

        return collection


# class ChromaClient():
#     def __init__(self, eb_custom:str = EMBEDDING_METHOD_CUSTOM, model_name=EMBEDDING_MODEL, api_key=GEMINI_API_KEY, 
#                  api_url=GOOGLE_API_URL, embedding_dim= EMBEDDING_DIMENSION,
#                  chroma_client_path=CHROMA_CLIENT_PATH):
        
        
#         if not eb_custom:
#             self.ef = custom_ef
#         else:
#             self.ef = DefaultEmbeddingFunction()

#         self.chroma_client = chromadb.PersistentClient(path=chroma_client_path)


#     def query_rag(self, query_texts:str, n_results:int, collection_name:str = DEFAULT_COLLECTION_NAME) -> chromadb.QueryResult:
#         collection = self._get_collection(collection_name)

#         results = collection.query(
#             query_texts=query_texts,
#             n_results=n_results
#         )
        
#         return results
    
#     def query_rag_with_width(self, query_texts:str, n_results:int, msg_width=10, collection_name:str = DEFAULT_COLLECTION_NAME) -> str:
#         collection = self._get_collection(collection_name)

#         results = collection.query(
#             query_texts=query_texts,
#             n_results=n_results
#         )
        
#         return self.get_width_message(results, msg_width)
    
#     @staticmethod
#     def get_width_message(results:chromadb.QueryResult, msg_width=10) -> str:
#         docs = results['documents'][0]
#         ids = results['ids'][0]
#         obj = [get_range_message_by_msg_width(rag_id, msg_width=msg_width) for rag_id in ids]
        
#         if obj:
#             contents = []
#             for o, rag_id in zip(obj, ids):
#                 g_id, ch_id, id = rag_id.split('_')
#                 ch_id_save = g_id + '_' + ch_id + '_'
#                 # conts = [(f"{ch_id_save}{m['id']}", (
#                 #     (f"message:{m['message']}," if m['message'] else "message: send a attachment,") 
#                 #     + f" send from:{m['author_name']}, time:{m['date']}."
#                 #     + (f"\nThis message is in reply to:{m['replied_message']}" if m['replied_message'] else "")
#                 # ))
#                 #         for m in o]

#                 conts = get_contents_str_by_messages(o, ch_id_save)
#                 contents += conts

#             contents = list(set(contents)) # 去除list中重複的元素
#             ids, docs = zip(*contents)
#             output_text = reults_to_llm_input(ids, docs)

#             return output_text

#         else :
#             return "Got no one message."

        
    
#     def _get_collection(self, collection_name:str) -> chromadb.Collection:
#         try:
#             collection = self.chroma_client.get_collection(name=collection_name, embedding_function=self.ef)

#         except chromadb.errors.NotFoundError:
#             collection = self.chroma_client.create_collection(name=collection_name, embedding_function=self.ef)

#         return collection




# class ChromaGeminiClient():
#     def __init__(self, eb_custom:str = EMBEDDING_METHOD_CUSTOM, model_name=EMBEDDING_MODEL, api_key=GEMINI_API_KEY, 
#                  api_url=GOOGLE_API_URL, embedding_dim= EMBEDDING_DIMENSION,
#                  chroma_client_path=CHROMA_CLIENT_PATH):
        
        
#         if not eb_custom:
#             self.ef = custom_ef
#         else:
#             self.ef = DefaultEmbeddingFunction()

#         self.chroma_client = chromadb.PersistentClient(path=chroma_client_path)


#     def query_rag(self, query_texts:str, n_results:int, collection_name:str = DEFAULT_COLLECTION_NAME) -> chromadb.QueryResult:
#         collection = self._get_collection(collection_name)

#         results = collection.query(
#             query_texts=query_texts,
#             n_results=n_results
#         )
        
#         return results
    
#     def query_rag_with_width(self, query_texts:str, n_results:int, msg_width=10, collection_name:str = DEFAULT_COLLECTION_NAME) -> str:
#         collection = self._get_collection(collection_name)

#         results = collection.query(
#             query_texts=query_texts,
#             n_results=n_results
#         )
        
#         return self.get_width_message(results, msg_width)
    
#     @staticmethod
#     def get_width_message(results:chromadb.QueryResult, msg_width=10) -> str:
#         docs = results['documents'][0]
#         ids = results['ids'][0]
#         obj = [get_range_message_by_msg_width(rag_id, msg_width=msg_width) for rag_id in ids]
        
#         if obj:
#             contents = []
#             for o, rag_id in zip(obj, ids):
#                 g_id, ch_id, id = rag_id.split('_')
#                 ch_id_save = g_id + '_' + ch_id + '_'
#                 # conts = [(f"{ch_id_save}{m['id']}", (
#                 #     (f"message:{m['message']}," if m['message'] else "message: send a attachment,") 
#                 #     + f" send from:{m['author_name']}, time:{m['date']}."
#                 #     + (f"\nThis message is in reply to:{m['replied_message']}" if m['replied_message'] else "")
#                 # ))
#                 #         for m in o]

#                 conts = get_contents_str_by_messages(o, ch_id_save)
#                 contents += conts

#             contents = list(set(contents)) # 去除list中重複的元素
#             ids, docs = zip(*contents)
#             output_text = reults_to_llm_input(ids, docs)

#             return output_text

#         else :
#             return "Got no one message."

        
    
#     def _get_collection(self, collection_name:str) -> chromadb.Collection:
#         try:
#             collection = self.chroma_client.get_collection(name=collection_name, embedding_function=self.ef)

#         except chromadb.errors.NotFoundError:
#             collection = self.chroma_client.create_collection(name=collection_name, embedding_function=self.ef)

#         return collection





def get_range_message_by_msg_width(rag_id:str, msg_width:int = 10, ignore_ch:set[int]|None=None) -> list[dict]:
    '''
    拿到指定 message，並回傳前後 msg_width 個的訊息 
    '''
    g_id, ch_id, id = rag_id.split('_')
    target = int(id)
    if target in ignore_ch:
        skip = target-msg_width if target >= msg_width else None
        stop = target+msg_width
        with open(f"{CHAT_FOLD}/{g_id}/{ch_id}.jsonl", "r", encoding="utf-8") as f:
            obj = [json.loads(line) for line in islice(f, skip, stop)]

        return obj
    else: return None

def reults_to_llm_input(ids:list[str], docs:list[str]) -> str:
    '''
    ids : [gid_chid_id,]
    docs : [messages,]
    '''
    try : 
        with open(SERVER_INFO_FILE_PATH, 'r') as f:
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


def get_today_messages_outputs(ch_id:str, max_outputs:int=100):
    dc_tem = get_tum_num()
    g_id = str(dc_tem[ch_id]['guild_id'])
    ch_id_save = g_id+'_'+ch_id+'_'

    today = datetime.now().date()
    obj = get_date_messages(ch_id, today, max_outputs=max_outputs)
    if obj:
        contents = get_contents_str_by_messages(obj, ch_id_save)
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

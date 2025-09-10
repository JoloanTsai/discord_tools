import asyncio
import random
import time
from openai import AsyncOpenAI
from collections import deque

class LlmClient():
    def __init__(self, model_name, api_key, api_base_url, rpm=30, 
                 stream=False, temperature=0.05):
        self.model=model_name
        self.stream=stream
        self.temperature=temperature
        self.client = AsyncOpenAI(
            # This is the default and can be omitted
            api_key=api_key, 
            base_url=api_base_url
        )
        self.rpm = rpm
        self.requests = deque()
        self._lock = asyncio.Lock()

    async def run(self):
        await self.add_request()
        # dojob()
        print('this')

    async def invoke(self, messages:list[dict])-> str:
        self.add_request()
        response =await self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            stream=self.stream,
            temperature=self.temperature,
        )
        return response.choices[0].message.content
    
    async def invoke_json_response(self, messages:list[dict]):
        await self.add_request()
        response =await self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            stream=self.stream,
            temperature=self.temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    

    async def add_request(self):
        async with self._lock:
            while True:
                now = time.time()

                # 移除過期的 request
                while self.requests and self.requests[0] < now - 60:
                    self.requests.popleft()

                if len(self.requests) < self.rpm:
                    self.requests.append(now)
                    return

                wait_time = 60 - (now - self.requests[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

class LlmClientPool():
    def __init__(self, machines:list):
        self.workers = machines
        self.worker_num:int = len(machines)
        self._queue = asyncio.Queue()
        for m in machines:
            self._queue.put_nowait(m)

    async def acquire(self):
        return await self._queue.get()

    async def release(self, machine):
        self._queue.put_nowait(machine)


class EmbeddingClient():
    def __init__(self, model_name, api_key, api_base_url, tpm=100, dimensions=1536):
        self.model=model_name
        self.dimensions = dimensions
        self.tpm = tpm
        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url=api_base_url
        )

    async def embedding(self, docs:list[str]) -> list[list]:
        response = await self.client.embeddings.create(
            input=docs,
            model=self.model,
            dimensions=self.dimensions
            
        )
        return [item.embedding for item in response.data]
    
    async def get_id_doc_embedding(self, ids:list[str], docs:list[str]) -> list[tuple[str, str, list]]:
        embeddings = await self.embedding(docs)
        # print([(id_, doc_, emb_) for id_, doc_, emb_ in zip(ids, docs, embeddings)])

        return [(id_, doc_, emb_) for id_, doc_, emb_ in zip(ids, docs, embeddings)]
    
    
class EmbeddingClientPool():
    '''
    執行後休息 1min 所以一次使用最大的 RPM 最有效率
    '''
    def __init__(self, machines:list):
        self.workers = machines
        self.worker_num:int = len(machines)
        self._queue = asyncio.Queue()
        for m in machines:
            self._queue.put_nowait(m)

    async def acquire(self):
        return await self._queue.get()

    async def release(self, machine):
        await asyncio.sleep(59)
        self._queue.put_nowait(machine)




async def pool_ai_invoke(pool, message):
    machine = await pool.acquire()
    # return await machine.invoke(message)
    print(machine)
    a = await machine.invoke(message)
    print(a)
    pool.release(machine)

    # try:
    #     # return await machine.invoke(message)
    #     print(machine)
    #     a = await machine.invoke(message)
    #     print(a)
    # finally:
    #     pool.release(machine)


if __name__ == '__main__':
    pass

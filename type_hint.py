from typing import TypedDict

class LlmOutputWithRagid(TypedDict):
    output_text:str
    rag_ids:list

class Message(TypedDict):
    id:int
    message:str
    message_id:int
    attachment_urls:list[str]
    date:str # isoformat
    author_id:int
    author_name:str
    mentions:list[str] | None
    replied_message:str | None
    replied_message_id:int | None
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


query_rag_with_rag_id_response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "API_Response_Schema",
        "schema": {
            "name": "math_response",
            "type": "object",
            "properties": {
                "output": {
                    "type": "string",
                    "description": "The main output by system prompt."
                },
                "mention_messages": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "從 query_output 訊息中，和你剛剛決定的 output，如果你看到覺得讓使用者看到會很有幫助的對話，就將 rag_id 放在 'mention_message':list[str] 裡面，記住不要太多，最多輸出 2 個，然後不要沒事就輸出，覺得沒有非常有幫助的話就輸出空 list[] 就好，謹慎評估。"
                    }
                }
            },
            "required": ["output", "mention_messages"], # 這裡的鍵名要和上面對應
            "additionalProperties": False
        }
    }
}
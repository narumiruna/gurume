from typing import Final

from dotenv import find_dotenv
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

PROMPT: Final[str] = """
あなたは食べログの検索用に最適化された日本語の自然言語処理モデルです。以下のユーザー入力から、食べログで検索に使う「area（エリア）」と「keyword（キーワード）」を抽出してください。

【重要】出力ルール：
1. キーは "area" と "keyword"
2. 値は**必ず日本語で出力してください**（中国語・英語などの入力でも必ず日本語に翻訳すること）
3. エリアは地名を簡潔に（例: 東京、新宿、渋谷など）
4. キーワードは料理名やジャンル（例: 寿喜焼き、ラーメン、居酒屋など）
5. 値が特定できない場合は空文字 ("") を返してください

【翻訳例】
- 入力「我想吃三重的壽喜燒」→ area: "三重", keyword: "すき焼き"
- 入力「台北的拉麵」→ area: "台北", keyword: "ラーメン"
- 入力「sushi in Tokyo」→ area: "東京", keyword: "寿司"
- 入力「大阪難波附近的居酒屋」→ area: "大阪難波", keyword: "居酒屋"

ユーザー入力:
{user_input}
""".strip()


class SearchRequest(BaseModel):
    area: str
    keyword: str


def parse_user_input(user_input: str) -> SearchRequest:
    load_dotenv(find_dotenv())

    client = OpenAI()
    response = client.responses.parse(
        model="gpt-4.1",
        input=PROMPT.format(user_input=user_input),
        text_format=SearchRequest,
    )

    if response.output_parsed is None:
        raise ValueError("Failed to parse user input")

    return response.output_parsed

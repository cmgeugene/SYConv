from pydantic import BaseModel
from typing import List

class ParsedWord(BaseModel):
    word: str
    pos: str
    meaning: str
    is_idiom: bool
    bbox: List[int]

class ProcessResponse(BaseModel):
    status: str
    filename: str
    data: List[ParsedWord]

class OCRWord(BaseModel):
    text: str
    bbox: List[int]

class ChunkData(BaseModel):
    chunk_index: int
    words: List[OCRWord]
    full_text: str = ""
    chunk_bbox: List[int] = []

class ExtractHighlightsResponse(BaseModel):
    status: str
    filename: str
    chunks: List[ChunkData]
    all_ocr_results: List[OCRWord] = []

class ParseWordsRequest(BaseModel):
    chunks: List[ChunkData]

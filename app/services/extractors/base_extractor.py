import requests
from typing import Type, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class BaseExtractor:
    def __init__(self, api_key: str, api_url: str, text_model_id: str, image_model_id: str):
        self.api_key = api_key
        self.api_url = api_url
        self.text_model_id = text_model_id
        self.image_model_id = image_model_id


    def _call_api(self, prompt: str, response_model: Type[T], image_part: Optional[dict] = None) -> T:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        content_list = [{"type": "text", "text": prompt}]
        if image_part:
            content_list.append(image_part)

        model = self.image_model_id if image_part else self.text_model_id
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 4096
        }

        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
                response.raise_for_status()

                result_data = response.json()
                content = result_data["choices"][0]["message"]["content"]
                return response_model.model_validate_json(content)
            except Exception as e:
                last_exception = e
                print(f"Attempt {attempt + 1}/{max_retries} failed with error: {e}")

        raise last_exception

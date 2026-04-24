"""
Клиент для API-генерации изображений.

Поддерживает два провайдера:
- nanobanana: Google AI Studio / Gemini / Imagen
- chatgpt: OpenAI Images API (`gpt-image-2`)
"""
import base64
import json
import os
import shutil
import tempfile
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from io import BytesIO
from typing import Optional

try:
    from google import genai
    from google.genai import types
    from PIL import Image

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    types = None
    Image = None

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


PROVIDER_NANOBANANA = "nanobanana"
PROVIDER_CHATGPT = "chatgpt"
DEFAULT_PROVIDER = PROVIDER_NANOBANANA
SUPPORTED_PROVIDERS = {PROVIDER_NANOBANANA, PROVIDER_CHATGPT}

_current_session_folder = None


def normalize_provider(provider: str | None) -> str:
    normalized = str(provider or DEFAULT_PROVIDER).strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        return DEFAULT_PROVIDER
    return normalized


def get_provider_display_name(provider: str) -> str:
    provider = normalize_provider(provider)
    if provider == PROVIDER_CHATGPT:
        return "chatgpt"
    return "nanobanana"


def get_session_output_folder() -> str:
    global _current_session_folder

    if _current_session_folder is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _current_session_folder = os.path.join("generated_images", timestamp)
        os.makedirs(_current_session_folder, exist_ok=True)

    return _current_session_folder


def reset_session_folder():
    global _current_session_folder
    _current_session_folder = None


def get_api_provider(settings: dict, with_reference: bool = False) -> str:
    key = "API_PROVIDER_WITH_REFS" if with_reference else "API_PROVIDER"
    provider = normalize_provider(settings.get(key, DEFAULT_PROVIDER))
    if with_reference and provider == PROVIDER_CHATGPT:
        return PROVIDER_CHATGPT
    return provider


def get_api_key_field(provider: str) -> str:
    provider = normalize_provider(provider)
    if provider == PROVIDER_CHATGPT:
        return "API_KEY_CHATGPT"
    return "API_KEY_NANOBANANA"


def get_api_key(settings: dict, provider: str) -> str:
    provider = normalize_provider(provider)
    key = str(settings.get(get_api_key_field(provider), "") or "").strip()
    if key:
        return key
    if provider == PROVIDER_NANOBANANA:
        return str(settings.get("API_KEY", "") or "").strip()
    return ""


def get_api_model(settings: dict, provider: str, with_reference: bool = False) -> str:
    provider = normalize_provider(provider)
    if provider == PROVIDER_CHATGPT:
        return str(settings.get("API_MODEL_CHATGPT", "gpt-image-2") or "gpt-image-2").strip()
    if with_reference:
        return str(settings.get("API_MODEL_WITH_REFS", "gemini-2.5-flash-image") or "gemini-2.5-flash-image").strip()
    return str(settings.get("API_MODEL", "imagen-4.0-generate-001") or "imagen-4.0-generate-001").strip()


def get_api_quality(settings: dict, provider: str) -> str:
    provider = normalize_provider(provider)
    if provider == PROVIDER_CHATGPT:
        return str(settings.get("API_CHATGPT_QUALITY", "low") or "low").strip().lower()
    return ""


def build_prompt(prompt: str, provider: str, aspect_ratio: str | None = None) -> str:
    provider = normalize_provider(provider)
    prompt = (prompt or "").strip()
    if provider == PROVIDER_CHATGPT and aspect_ratio:
        return f"ar - {aspect_ratio}. {prompt}"
    return prompt


def init_client(api_key: str, provider: str = DEFAULT_PROVIDER):
    provider = normalize_provider(provider)

    if not api_key or not api_key.strip():
        raise ValueError("API ключ не может быть пустым")

    if provider == PROVIDER_CHATGPT:
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "Библиотека openai не установлена. Выполните: pip install openai"
            )
        return OpenAI(api_key=api_key)

    if not GENAI_AVAILABLE:
        raise ImportError(
            "Библиотека google-genai не установлена. Выполните: pip install google-genai"
        )

    os.environ["GOOGLE_API_KEY"] = api_key
    return genai.Client(api_key=api_key)


def _generate_image_nanobanana(
    client,
    prompt: str,
    model: str,
    aspect_ratio: str,
    image_size: str,
) -> tuple[Optional[bytes], Optional[str]]:
    is_imagen4 = model.startswith("imagen-4")

    if is_imagen4:
        supported_ratios = ["1:1", "4:3", "3:4", "16:9", "9:16"]
        if aspect_ratio not in supported_ratios:
            return None, (
                f"Aspect ratio {aspect_ratio} не поддерживается Imagen 4. "
                f"Поддерживаются: {', '.join(supported_ratios)}"
            )

    if is_imagen4:
        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        )
        response = client.models.generate_images(
            model=model,
            prompt=prompt,
            config=config,
        )
        if not response:
            return None, "API вернул пустой response объект"
        if not getattr(response, "generated_images", None):
            return None, f"API response не содержит generated_images. Response: {response}"

        image_bytes = response.generated_images[0].image.image_bytes
        if isinstance(image_bytes, bytes):
            return image_bytes, None
        if isinstance(image_bytes, str):
            try:
                return base64.b64decode(image_bytes), None
            except Exception as e:
                return None, f"Ошибка декодирования base64: {e}"
        return None, f"Неожиданный тип image_bytes: {type(image_bytes)}"

    config_params = {"response_modalities": ["IMAGE"]}
    if "3-pro" in model or "pro-image" in model:
        config_params["image_config"] = types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        )
    else:
        config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(**config_params),
    )
    if not response:
        return None, "API вернул пустой response объект"
    if not getattr(response, "parts", None):
        error_msg = f"API response не содержит parts. Response: {response}"
        if hasattr(response, "prompt_feedback"):
            error_msg += f" | prompt_feedback: {response.prompt_feedback}"
        if hasattr(response, "candidates"):
            error_msg += f" | candidates: {response.candidates}"
        return None, error_msg

    for part in response.parts:
        if part.inline_data is None:
            continue
        image_data = part.inline_data.data
        if isinstance(image_data, bytes):
            return image_data, None
        if isinstance(image_data, str):
            try:
                return base64.b64decode(image_data), None
            except Exception as e:
                return None, f"Ошибка декодирования base64: {e}"
        if hasattr(part, "as_image"):
            try:
                img_obj = part.as_image()
                if Image and isinstance(img_obj, Image.Image):
                    img_bytes = BytesIO()
                    img_obj.save(img_bytes, format="PNG")
                    return img_bytes.getvalue(), None
            except Exception:
                pass
        if image_data:
            return image_data, None

    parts_info = [
        f"part {i}: {type(part).__name__}, inline_data={part.inline_data is not None}"
        for i, part in enumerate(response.parts)
    ]
    return None, f"Нет inline_data в response.parts. Parts: {', '.join(parts_info)}"


def _generate_image_chatgpt(
    client,
    prompt: str,
    model: str,
    aspect_ratio: str,
    quality: str,
    timeout: float,
) -> tuple[Optional[bytes], Optional[str]]:
    request_client = client.with_options(timeout=timeout) if hasattr(client, "with_options") else client
    response = request_client.images.generate(
        model=model,
        prompt=build_prompt(prompt, PROVIDER_CHATGPT, aspect_ratio),
        n=1,
        size="auto",
        quality=quality or "low",
    )

    if not response:
        return None, "API вернул пустой response объект"
    data = getattr(response, "data", None)
    if not data:
        return None, f"API response не содержит data. Response: {response}"

    image_item = data[0]
    b64_json = getattr(image_item, "b64_json", None)
    if b64_json is None and isinstance(image_item, dict):
        b64_json = image_item.get("b64_json")
    if not b64_json:
        return None, f"API response не содержит b64_json. Response: {response}"

    try:
        return base64.b64decode(b64_json), None
    except Exception as e:
        return None, f"Ошибка декодирования b64_json: {e}"


def generate_image(
    client,
    prompt: str,
    model: str = "imagen-4.0-generate-001",
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    timeout: float = 60.0,
    provider: str = DEFAULT_PROVIDER,
    quality: str = "low",
) -> tuple[Optional[bytes], Optional[str]]:
    if not prompt or not prompt.strip():
        return None, "Пустой промпт"

    provider = normalize_provider(provider)
    try:
        if provider == PROVIDER_CHATGPT:
            return _generate_image_chatgpt(
                client=client,
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                quality=quality,
                timeout=timeout,
            )

        if not GENAI_AVAILABLE:
            return None, "Библиотека google-genai не доступна"

        return _generate_image_nanobanana(
            client=client,
            prompt=prompt,
            model=model,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
        )
    except Exception as e:
        return None, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def fetch_openai_costs(
    api_key: str,
    start_time: int,
    end_time: int,
    bucket_width: str = "1h",
) -> tuple[Optional[float], Optional[str]]:
    api_key = str(api_key or "").strip()
    if not api_key:
        return None, "пустой API ключ"
    if end_time <= start_time:
        return None, "некорректный интервал времени"

    query = urllib.parse.urlencode(
        {
            "start_time": int(start_time),
            "end_time": int(end_time),
            "bucket_width": bucket_width,
        }
    )
    url = f"https://api.openai.com/v1/organization/costs?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        return None, f"HTTP {e.code}: {body or e.reason}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

    total_cost = 0.0
    found_amount = False
    for bucket in payload.get("data", []) or []:
        results = bucket.get("result") or bucket.get("results") or []
        for item in results:
            amount = item.get("amount") or {}
            value = amount.get("value")
            if value is None:
                continue
            try:
                total_cost += float(value)
                found_amount = True
            except (TypeError, ValueError):
                continue

    if not found_amount:
        return None, "в ответе Costs API нет данных по расходам"
    return total_cost, None


def generate_image_with_reference(
    client,
    prompt: str,
    reference_image_path: str,
    model: str = "gemini-2.5-flash-image",
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    timeout: float = 60.0,
    provider: str = DEFAULT_PROVIDER,
    quality: str = "low",
) -> tuple[Optional[bytes], Optional[str]]:
    if not prompt or not prompt.strip():
        return None, "Пустой промпт"

    provider = normalize_provider(provider)
    if provider == PROVIDER_CHATGPT:
        return None, (
            "ChatGPT API для генерации с референсами в этом режиме пока не поддержан. "
            "Для задач с референсами используйте nanobanana."
        )

    if not GENAI_AVAILABLE:
        return None, "Библиотека google-genai не доступна"

    if model.startswith("imagen-4"):
        return None, "Модель Imagen 4 не поддерживает референсные изображения. Используйте Gemini."

    if not reference_image_path or not os.path.exists(reference_image_path):
        return None, f"Референсное изображение не найдено: {reference_image_path}"

    try:
        tmp_path = None
        try:
            abs_path = os.path.abspath(reference_image_path)
            suffix = os.path.splitext(abs_path)[1].lower()
            if suffix not in (".png", ".jpg", ".jpeg"):
                suffix = ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp_path = tmp.name
            shutil.copy2(abs_path, tmp_path)
            uploaded_file = client.files.upload(file=tmp_path)
        finally:
            if tmp_path is not None and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        config_params = {"response_modalities": ["IMAGE"]}
        if "3-pro" in model or "pro-image" in model:
            config_params["image_config"] = types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )
        else:
            config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)

        response = client.models.generate_content(
            model=model,
            contents=[prompt, uploaded_file],
            config=types.GenerateContentConfig(**config_params),
        )
        if not response:
            return None, "API вернул пустой response объект"
        if not getattr(response, "parts", None):
            error_msg = f"API response не содержит parts. Response: {response}"
            if hasattr(response, "prompt_feedback"):
                error_msg += f" | prompt_feedback: {response.prompt_feedback}"
            if hasattr(response, "candidates"):
                error_msg += f" | candidates: {response.candidates}"
            return None, error_msg

        for part in response.parts:
            if part.inline_data is None:
                continue
            image_data = part.inline_data.data
            if isinstance(image_data, bytes):
                return image_data, None
            if isinstance(image_data, str):
                try:
                    return base64.b64decode(image_data), None
                except Exception as e:
                    return None, f"Ошибка декодирования base64: {e}"
            if hasattr(part, "as_image"):
                try:
                    img_obj = part.as_image()
                    if Image and isinstance(img_obj, Image.Image):
                        img_bytes = BytesIO()
                        img_obj.save(img_bytes, format="PNG")
                        return img_bytes.getvalue(), None
                except Exception:
                    pass
            if image_data:
                return image_data, None

        parts_info = [
            f"part {i}: {type(part).__name__}, inline_data={part.inline_data is not None}"
            for i, part in enumerate(response.parts)
        ]
        return None, f"Нет inline_data в response.parts. Parts: {', '.join(parts_info)}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def save_image_bytes(image_bytes: bytes, file_path: str) -> bool:
    if not image_bytes:
        return False

    try:
        session_folder = get_session_output_folder()
        full_path = os.path.join(session_folder, file_path)
        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        if Image is not None:
            img = Image.open(BytesIO(image_bytes))
            img.save(full_path, format="PNG")
        else:
            with open(full_path, "wb") as f:
                f.write(image_bytes)
        return True
    except Exception:
        return False


def check_api_key_format(api_key: str, provider: str = DEFAULT_PROVIDER) -> tuple[bool, str]:
    provider = normalize_provider(provider)
    api_key = str(api_key or "").strip()

    if not api_key:
        return False, "API ключ не может быть пустым"

    if provider == PROVIDER_CHATGPT:
        if len(api_key) < 20:
            return False, "API ключ ChatGPT слишком короткий"
        return True, ""

    if len(api_key) < 30:
        return False, "API ключ слишком короткий (должен быть ~39 символов)"
    if not api_key.startswith("AIza"):
        return False, "API ключ должен начинаться с 'AIza'"
    return True, ""

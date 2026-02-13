"""
Клиент для работы с Gemini API (генерация изображений через API вместо браузера).
Обёртка над google-genai SDK для модели gemini-2.5-flash-image.
"""
import os
import time
import base64
import traceback
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


def init_client(api_key: str):
    """
    Инициализация клиента Gemini API.
    
    Args:
        api_key: API ключ Google AI Studio
        
    Returns:
        genai.Client или None при ошибке
        
    Raises:
        ImportError: если библиотека google-genai не установлена
        ValueError: если api_key пустой
    """
    if not GENAI_AVAILABLE:
        raise ImportError(
            "Библиотека google-genai не установлена. "
            "Выполните: pip install google-genai"
        )
    
    if not api_key or not api_key.strip():
        raise ValueError("API ключ не может быть пустым")
    
    # Инициализация клиента (API ключ можно передать через переменную окружения или явно)
    # Документация: https://ai.google.dev/gemini-api/docs/imagen
    os.environ["GOOGLE_API_KEY"] = api_key
    client = genai.Client(api_key=api_key)
    return client


def generate_image(
    client,
    prompt: str,
    model: str = "gemini-2.5-flash-image",
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    timeout: float = 60.0,
) -> tuple[Optional[bytes], Optional[str]]:
    """
    Генерация одного изображения через Gemini API.
    
    Args:
        client: экземпляр genai.Client
        prompt: текст промпта для генерации
        model: название модели (gemini-2.5-flash-image или gemini-3-pro-image-preview)
        aspect_ratio: соотношение сторон ("1:1", "4:3", "3:4", "16:9", "9:16")
        image_size: разрешение для Pro модели ("1K", "2K", "4K"; для flash не применяется)
        timeout: таймаут запроса в секундах
        
    Returns:
        (bytes изображения в формате PNG или None, строка с ошибкой или None)
    """
    if not GENAI_AVAILABLE:
        return None, "Библиотека google-genai не доступна"
    
    if not prompt or not prompt.strip():
        return None, "Пустой промпт"
    
    try:
        # Конфигурация генерации (для Gemini 3 Pro Image можно указать image_size)
        # Для gemini-2.5-flash-image параметр image_size игнорируется
        config_params = {
            "response_modalities": ["IMAGE"],
        }
        
        # Для моделей, поддерживающих image_config (Gemini 3 Pro Image Preview)
        if "3-pro" in model or "pro-image" in model:
            config_params["image_config"] = types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )
        
        config = types.GenerateContentConfig(**config_params)
        
        # Генерация изображения
        # По документации: response.parts содержит inline_data с изображением
        response = client.models.generate_content(
            model=model,
            contents=[prompt],
            config=config,
        )
        
        # Проверка наличия ответа
        if not response:
            return None, "API вернул пустой response объект"
        
        # Проверка наличия parts в ответе
        if not hasattr(response, 'parts') or not response.parts:
            error_msg = f"API response не содержит parts. Response: {response}"
            # Проверка наличия prompt_feedback (блокировка контента)
            if hasattr(response, 'prompt_feedback'):
                error_msg += f" | prompt_feedback: {response.prompt_feedback}"
            # Проверка candidates (альтернативные результаты)
            if hasattr(response, 'candidates'):
                error_msg += f" | candidates: {response.candidates}"
            return None, error_msg
        
        # Извлечение изображения из ответа
        # response.parts - список Part объектов
        # Изображение находится в part.inline_data
        for part in response.parts:
            if part.inline_data is not None:
                # inline_data.data содержит изображение в виде bytes
                # Прямой доступ к данным - самый надёжный способ
                image_data = part.inline_data.data
                
                # Проверяем, что это bytes
                if isinstance(image_data, bytes):
                    return image_data, None
                
                # Если это строка (base64), декодируем
                if isinstance(image_data, str):
                    try:
                        return base64.b64decode(image_data), None
                    except Exception as e:
                        return None, f"Ошибка декодирования base64: {e}"
                
                # Если есть метод as_image() - используем как fallback
                if hasattr(part, "as_image"):
                    try:
                        img_obj = part.as_image()
                        # Если это PIL Image
                        if Image and isinstance(img_obj, Image.Image):
                            img_bytes = BytesIO()
                            img_obj.save(img_bytes, format="PNG")
                            return img_bytes.getvalue(), None
                    except Exception as e:
                        # Если не получилось с as_image - возвращаем прямые данные
                        if image_data:
                            return image_data, None
                        return None, f"Ошибка конвертации as_image: {e}"
                
                # Если ничего не подошло, но данные есть - возвращаем как есть
                if image_data:
                    return image_data, None
        
        # Если дошли сюда - нет inline_data ни в одном part
        parts_info = [f"part {i}: {type(part).__name__}, inline_data={part.inline_data is not None}" 
                      for i, part in enumerate(response.parts)]
        return None, f"Нет inline_data в response.parts. Parts: {', '.join(parts_info)}"
        
    except Exception as e:
        # Ошибки API: rate limits, invalid key, network issues
        # Возвращаем детальную информацию об ошибке
        error_type = type(e).__name__
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        detailed_error = f"{error_type}: {error_msg}\n{error_trace}"
        return None, detailed_error


def save_image_bytes(image_bytes: bytes, file_path: str) -> bool:
    """
    Сохранение байтов изображения в файл PNG.
    
    Args:
        image_bytes: байты изображения
        file_path: путь для сохранения (включая имя файла)
        
    Returns:
        True при успешном сохранении, False при ошибке
    """
    if not image_bytes:
        return False
    
    try:
        # Создание директории если не существует
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Сохранение байтов как PNG через PIL (для проверки валидности)
        if GENAI_AVAILABLE and Image:
            img = Image.open(BytesIO(image_bytes))
            img.save(file_path, format="PNG")
        else:
            # Fallback: прямая запись байтов
            with open(file_path, "wb") as f:
                f.write(image_bytes)
        
        return True
        
    except Exception:
        return False


def check_api_key_format(api_key: str) -> tuple[bool, str]:
    """
    Проверка формата API ключа Google AI Studio.
    
    Args:
        api_key: строка с API ключом
        
    Returns:
        (valid, error_message) - True/пустая строка если ключ валиден,
        False/сообщение об ошибке если невалиден
    """
    if not api_key or not api_key.strip():
        return False, "API ключ не может быть пустым"
    
    # Google AI Studio API ключи обычно начинаются с "AIza"
    # Длина примерно 39 символов
    api_key = api_key.strip()
    
    if len(api_key) < 30:
        return False, "API ключ слишком короткий (должен быть ~39 символов)"
    
    if not api_key.startswith("AIza"):
        return False, "API ключ должен начинаться с 'AIza'"
    
    return True, ""

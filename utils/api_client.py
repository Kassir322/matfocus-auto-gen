"""
Клиент для работы с Gemini API (генерация изображений через API вместо браузера).
Обёртка над google-genai SDK для моделей Imagen 4 и старых моделей Gemini.
Поддерживает: imagen-4.0-fast/generate/ultra, gemini-2.5-flash-image.
"""
import os
import shutil
import tempfile
import time
import base64
import traceback
from io import BytesIO
from typing import Optional
from datetime import datetime

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


# Глобальная переменная для хранения папки текущей сессии
_current_session_folder = None


def get_session_output_folder() -> str:
    """
    Возвращает путь к папке для сохранения изображений текущей сессии.
    Папка создается один раз при первом вызове и используется для всей сессии.
    Формат: generated_images/YYYY-MM-DD_HH-MM-SS/
    
    Returns:
        str: путь к папке сессии
    """
    global _current_session_folder
    
    if _current_session_folder is None:
        # Создать папку с датой/временем для текущей сессии
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _current_session_folder = os.path.join("generated_images", timestamp)
        os.makedirs(_current_session_folder, exist_ok=True)
    
    return _current_session_folder


def reset_session_folder():
    """
    Сбросить папку сессии (для тестирования или при необходимости создать новую папку).
    Вызывается при старте новой сессии генерации.
    """
    global _current_session_folder
    _current_session_folder = None


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
    model: str = "imagen-4.0-generate-001",
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    timeout: float = 60.0,
) -> tuple[Optional[bytes], Optional[str]]:
    """
    Генерация одного изображения через Gemini API.
    
    Поддерживает два типа моделей:
    - Imagen 4: imagen-4.0-fast-generate-001, imagen-4.0-generate-001, imagen-4.0-ultra-generate-001
    - Старые: gemini-2.5-flash-image, gemini-3-pro-image-preview
    
    Args:
        client: экземпляр genai.Client
        prompt: текст промпта для генерации
        model: название модели (по умолчанию imagen-4.0-generate-001)
        aspect_ratio: соотношение сторон ("1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "4:5", "5:4", "21:9")
        image_size: разрешение ("1K" или "2K" для Imagen 4; "1K", "2K", "4K" для Pro моделей)
        timeout: таймаут запроса в секундах
        
    Returns:
        (bytes изображения в формате PNG или None, строка с ошибкой или None)
    """
    if not GENAI_AVAILABLE:
        return None, "Библиотека google-genai не доступна"
    
    if not prompt or not prompt.strip():
        return None, "Пустой промпт"
    
    # Определяем тип модели для выбора API endpoint
    is_imagen4 = model.startswith("imagen-4")
    
    # Валидация aspect_ratio для Imagen 4 (поддерживаются только 1:1, 4:3, 3:4, 16:9, 9:16)
    if is_imagen4:
        supported_ratios = ["1:1", "4:3", "3:4", "16:9", "9:16"]
        if aspect_ratio not in supported_ratios:
            return None, (
                f"Aspect ratio {aspect_ratio} не поддерживается Imagen 4. "
                f"Поддерживаются: {', '.join(supported_ratios)}"
            )
    
    try:
        if is_imagen4:
            # ========== Imagen 4: используем generate_images API ==========
            # Документация: https://ai.google.dev/gemini-api/docs/imagen
            config = types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                image_size=image_size,  # "1K" или "2K"
            )
            
            response = client.models.generate_images(
                model=model,
                prompt=prompt,
                config=config,
            )
            
            # Проверка наличия ответа
            if not response:
                return None, "API вернул пустой response объект"
            
            # Проверка наличия generated_images
            if not hasattr(response, 'generated_images') or not response.generated_images:
                error_msg = f"API response не содержит generated_images. Response: {response}"
                return None, error_msg
            
            # Извлечение изображения из response.generated_images[0].image.image_bytes
            generated_image = response.generated_images[0]
            
            if not hasattr(generated_image, 'image') or not generated_image.image:
                return None, f"generated_image не содержит image. Object: {generated_image}"
            
            image_bytes = generated_image.image.image_bytes
            
            if not image_bytes:
                return None, "image_bytes пустой в generated_image.image"
            
            # image_bytes может быть строкой base64 или bytes
            if isinstance(image_bytes, bytes):
                return image_bytes, None
            elif isinstance(image_bytes, str):
                try:
                    return base64.b64decode(image_bytes), None
                except Exception as e:
                    return None, f"Ошибка декодирования base64 из image_bytes: {e}"
            else:
                return None, f"Неожиданный тип image_bytes: {type(image_bytes)}"
        
        else:
            # ========== Старые модели: используем generate_content API ==========
            config_params = {
                "response_modalities": ["IMAGE"],
            }
            
            # По документации: 2.5-flash-image — только aspect_ratio, 3-pro — aspect_ratio + image_size
            if "3-pro" in model or "pro-image" in model:
                config_params["image_config"] = types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                )
            else:
                config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)
            
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
            return None, f"Нет inline_data в response.parts. Parts: {', '.join(parts_info)}'"
        
    except Exception as e:
        # Ошибки API: rate limits, invalid key, network issues
        # Возвращаем детальную информацию об ошибке
        error_type = type(e).__name__
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        detailed_error = f"{error_type}: {error_msg}\n{error_trace}"
        return None, detailed_error


def generate_image_with_reference(
    client,
    prompt: str,
    reference_image_path: str,
    model: str = "gemini-2.5-flash-image",
    aspect_ratio: str = "1:1",
    image_size: str = "1K",
    timeout: float = 60.0,
) -> tuple[Optional[bytes], Optional[str]]:
    """
    Генерация изображения через Gemini API с референсным изображением.
    
    Поддерживает только мультимодальные модели (Gemini):
    - gemini-2.5-flash-image
    - gemini-3-pro-image-preview
    
    Args:
        client: экземпляр genai.Client
        prompt: текст промпта для генерации
        reference_image_path: путь к референсному изображению (локальный файл)
        model: название модели (должна быть мультимодальная Gemini)
        aspect_ratio: соотношение сторон ("1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "4:5", "5:4", "21:9")
        image_size: разрешение ("1K", "2K", "4K" для Gemini моделей)
        timeout: таймаут запроса в секундах
        
    Returns:
        (bytes изображения в формате PNG или None, строка с ошибкой или None)
    """
    if not GENAI_AVAILABLE:
        return None, "Библиотека google-genai не доступна"
    
    if not prompt or not prompt.strip():
        return None, "Пустой промпт"
    
    # Проверка модели: Imagen 4 не поддерживает референсы
    if model.startswith("imagen-4"):
        return None, "Модель Imagen 4 не поддерживает референсные изображения. Используйте gemini-2.5-flash-image"
    
    # Проверка наличия референсного файла
    if not reference_image_path or not os.path.exists(reference_image_path):
        return None, f"Референсное изображение не найдено: {reference_image_path}"
    
    try:
        # Загрузка референсного изображения через File API.
        # Пути с кириллицей (например data/images/лицо/70_лицо.jpg) вызывают ASCII encoding ошибку,
        # поэтому копируем файл во временный с ASCII-именем и загружаем его.
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
        except Exception as e:
            return None, f"Ошибка загрузки референсного изображения: {e}"
        finally:
            if tmp_path is not None and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        
        # Конфигурация для генерации с изображением
        config_params = {
            "response_modalities": ["IMAGE"],
        }
        
        # По документации: 2.5-flash-image — только aspect_ratio, 3-pro — aspect_ratio + image_size
        if "3-pro" in model or "pro-image" in model:
            config_params["image_config"] = types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )
        else:
            config_params["image_config"] = types.ImageConfig(aspect_ratio=aspect_ratio)
        
        config = types.GenerateContentConfig(**config_params)
        
        # Генерация с референсом: contents = [промпт, загруженный_файл]
        # Порядок важен: сначала текст, потом изображение
        response = client.models.generate_content(
            model=model,
            contents=[prompt, uploaded_file],
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
        
        # Извлечение изображения из ответа (аналогично generate_image для Gemini моделей)
        for part in response.parts:
            if part.inline_data is not None:
                # inline_data.data содержит изображение в виде bytes
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
        return None, f"Нет inline_data в response.parts. Parts: {', '.join(parts_info)}'"
        
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
    Сохранение байтов изображения в файл PNG в папке текущей сессии.
    
    Args:
        image_bytes: байты изображения
        file_path: имя файла (или путь относительно папки сессии)
        
    Returns:
        True при успешном сохранении, False при ошибке
    """
    if not image_bytes:
        return False
    
    try:
        # Получить папку текущей сессии
        session_folder = get_session_output_folder()
        
        # Если передан относительный путь с папками, сохранить структуру
        # Если передано только имя файла, сохранить в корень папки сессии
        full_path = os.path.join(session_folder, file_path)
        
        # Создание вложенных директорий если нужно
        directory = os.path.dirname(full_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        # Сохранение байтов как PNG через PIL (для проверки валидности)
        if GENAI_AVAILABLE and Image:
            img = Image.open(BytesIO(image_bytes))
            img.save(full_path, format="PNG")
        else:
            # Fallback: прямая запись байтов
            with open(full_path, "wb") as f:
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

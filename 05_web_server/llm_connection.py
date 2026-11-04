"""Neutral, bounded provider checks, independent of the research runtime."""
from __future__ import annotations

import json
import http.client
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from deepseek_live_smoke import NoRedirect, redact, usage_valid

HOSTS = {"deepseek": "api.deepseek.com", "openai": "api.openai.com"}
SUPPORTED_PROVIDERS = {"deepseek", "openai", "custom", "ollama"}
MARKER = "API_CONNECTION_OK"
_slots = threading.BoundedSemaphore(2)


class ConnectionCheckError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def validate_config(data: dict) -> tuple[str, str, str]:
    fields = {"provider", "api_key", "base_url", "model_name"}
    if not isinstance(data, dict) or set(data) != fields or any(not isinstance(data[k], str) for k in fields):
        raise ConnectionCheckError(422, "INVALID_CONFIG", "请提供服务商、密钥、接口地址和模型标识四个文本字段。")
    provider, key, base, model = (data[k].strip() for k in ("provider", "api_key", "base_url", "model_name"))
    if provider not in SUPPORTED_PROVIDERS:
        raise ConnectionCheckError(422, "UNSUPPORTED_PROVIDER", "连接测试目前仅支持 DeepSeek、OpenAI、Ollama 及自定义兼容接口。")
    if not key or len(key) > 512 or not key.isascii() or any(c.isspace() or ord(c) < 33 for c in key):
        raise ConnectionCheckError(422, "INVALID_KEY", "请填写有效的 API Key。")
    if not model or len(model) > 100 or any(not (c.isascii() and (c.isalnum() or c in "-._:/")) for c in model):
        raise ConnectionCheckError(422, "INVALID_MODEL", "请填写有效的模型标识。")
    try:
        parsed = urllib.parse.urlsplit(base)
    except Exception:
        raise ConnectionCheckError(422, "INVALID_ENDPOINT", "无效的服务地址 URL。")
    if not parsed.scheme or parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ConnectionCheckError(422, "INVALID_ENDPOINT", "服务地址必须为有效的 http 或 https URL。")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConnectionCheckError(422, "INVALID_ENDPOINT", "服务地址不可包含用户名、密码或查询参数。")

    path = parsed.path.rstrip("/")
    if provider in HOSTS:
        valid = (parsed.scheme == "https" and parsed.netloc.lower() == HOSTS[provider]
                 and path in ("", "/v1", "/chat/completions", "/v1/chat/completions"))
        if not valid or (provider == "openai" and path not in ("/v1", "/v1/chat/completions")):
            raise ConnectionCheckError(422, "INVALID_ENDPOINT", "请选择对应服务商的官方 HTTPS API 地址；第三方代理请在服务商中选择“自定义提供商 (Custom)”。")
        if not path.endswith("/chat/completions"):
            path += "/chat/completions"
        return key, "https://" + HOSTS[provider] + path, model
    else:
        if not path.endswith("/chat/completions"):
            path += "/chat/completions"
        endpoint = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
        return key, endpoint, model


def check_connection(data: dict) -> dict:
    key, endpoint, model = validate_config(data)
    provider = data["provider"].strip()
    if not _slots.acquire(blocking=False):
        raise ConnectionCheckError(429, "TEST_BUSY", "连接测试繁忙，请稍后手动重试。")
    started = time.perf_counter()
    try:
        payload = {"model": model, "temperature": 0, "stream": False, "max_tokens": 32,
                   "messages": [{"role": "user", "content": "Return exactly API_CONNECTION_OK. No other text."}]}
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "DTI-Studio/5.0.0"}, method="POST")
        opener = urllib.request.build_opener(NoRedirect()) if provider in HOSTS else urllib.request.build_opener()
        with opener.open(request, timeout=45) as response:
            body = response.read(65537)
            if response.status != 200 or len(body) > 65536:
                raise ValueError("invalid response")
        result = json.loads(body)
        if not isinstance(result, dict) or "choices" not in result or not isinstance(result["choices"], list) or not result["choices"]:
            raise ValueError("invalid response contract: missing choices")
        choice = result["choices"][0]
        if not isinstance(choice, dict) or "message" not in choice or not isinstance(choice["message"], dict):
            raise ValueError("invalid response contract: missing message")
        message = choice["message"]
        content = message.get("content", "")

        if provider in HOSTS:
            if (len(result["choices"]) != 1 or result.get("object") != "chat.completion"
                    or not isinstance(result.get("id"), str) or not result["id"]
                    or not isinstance(result.get("model"), str) or not result["model"]
                    or message.get("role") != "assistant" or str(content).strip() != MARKER
                    or choice.get("finish_reason") != "stop" or not usage_valid(result.get("usage"))):
                raise ValueError("invalid response contract")
            usage_data = {k: result["usage"][k] for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
        else:
            if not str(content).strip():
                raise ValueError("invalid response contract: empty content")
            raw_usage = result.get("usage")
            if isinstance(raw_usage, dict):
                usage_data = {
                    "prompt_tokens": int(raw_usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(raw_usage.get("completion_tokens") or 0),
                    "total_tokens": int(raw_usage.get("total_tokens") or 0),
                }
            else:
                usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        return redact({"status": "connected", "provider": provider,
                       "requested_model": model, "returned_model": str(result.get("model") or model)[:200],
                       "duration_seconds_full_response": round(time.perf_counter() - started, 4),
                       "usage": usage_data,
                       "scope": "neutral_connectivity_only"}, key)
    except urllib.error.HTTPError as exc:
        status = exc.code
        err_detail = ""
        try:
            err_body = exc.read(2048).decode("utf-8", errors="replace")
            err_json = json.loads(err_body)
            if isinstance(err_json, dict) and "error" in err_json:
                err_obj = err_json["error"]
                if isinstance(err_obj, dict):
                    err_detail = err_obj.get("display_message") or err_obj.get("localized_message") or err_obj.get("message") or ""
                elif isinstance(err_obj, str):
                    err_detail = err_obj
        except Exception:
            pass
        exc.close()
        errors = {401: ("AUTH_FAILED", "API Key 无效或已失效。"),
                  403: ("ACCESS_DENIED", "该凭证没有访问此模型的权限。"),
                  402: ("INSUFFICIENT_BALANCE", "服务商账户余额不足。"),
                  404: ("MODEL_NOT_FOUND", "接口或模型标识不存在。"),
                  429: ("PROVIDER_RATE_LIMITED", "服务商限流或配额不足，请稍后手动重试。")}
        code, message = errors.get(status, ("PROVIDER_ERROR", "服务商未完成请求，请检查官方服务状态和模型配置。"))
        if err_detail:
            err_detail = redact(err_detail, key)
            message = f"{message} (服务商信息: {err_detail[:150]})"
        raise ConnectionCheckError(502, code, message) from None
    except (TimeoutError, socket.timeout):
        raise ConnectionCheckError(504, "PROVIDER_TIMEOUT", "服务商响应超时，请稍后手动重试。") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise ConnectionCheckError(504, "PROVIDER_TIMEOUT", "服务商响应超时，请稍后手动重试。") from None
        raise ConnectionCheckError(502, "NETWORK_ERROR", "无法连接服务商，请检查后端网络与 TLS 连接。") from None
    except (OSError, http.client.HTTPException):
        raise ConnectionCheckError(502, "NETWORK_ERROR", "服务商连接中断，请稍后手动重试。") from None
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise ConnectionCheckError(502, "INVALID_PROVIDER_RESPONSE", "服务商响应未通过固定短文本、完成状态或用量校验。") from None
    finally:
        _slots.release()

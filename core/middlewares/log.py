import json
import time
from typing import Any
from urllib.parse import parse_qs

from asgiref.sync import iscoroutinefunction, markcoroutinefunction

from utils.log import logger


class LoggingMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __get_client_ip(self,request):
        ip_addresses = request.headers.get("x-forwarded-for")
        if ip_addresses:
            return ip_addresses.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def __extract_request_info(self,request, include_body=False):
        extra = {
            "ip_address": self.__get_client_ip(request),
            "path": request.path,
            "query_params": request.GET.dict(),
            "method": request.method,
            "protocol": request.scheme,
            "protocol_version": request.META.get("SERVER_PROTOCOL"),
            "content_type": request.headers.get("content-type"),
        }
        if not include_body:
            return extra
        content_type = extra["content_type"]
        if request.method not in ["GET", "HEAD", "OPTIONS"] and content_type:
            body = request.body
            parsed_body = "[binary]"
            # Parse body based on content type
            try:
                if "application" in content_type or "text" in content_type:
                    parsed_body = body.decode("utf-8")
                elif "multipart" in content_type:
                    parsed_body = "[multipart form data]"
                if "json" in content_type:
                    parsed_body = json.loads(parsed_body)
                elif "x-www-form-urlencoded" in content_type:
                    parsed_body = parse_qs(parsed_body)
                    # Convert lists of single values to single values
                    parsed_body = {
                        k: v[0] if len(v) == 1 else v
                        for k, v in parsed_body.items()
                    }
            except (UnicodeDecodeError, json.JSONDecodeError):
                parsed_body = "[Failed to parse request body]"

            def filter_sensitive_data(data: Any):
                if isinstance(data, dict):
                    return {
                        k: "[censored]"
                        if "password" in str(k).lower()
                        and isinstance(v, str | list)
                        else filter_sensitive_data(v)
                        for k, v in data.items()
                    }
                elif isinstance(data, list):
                    return [filter_sensitive_data(item) for item in data]
                return data

            extra["body"] = filter_sensitive_data(parsed_body)
        return extra

    async def __call__(self, request):
        extra = self.__extract_request_info(request)
        start = time.perf_counter()
        response = await self.get_response(request)
        process_duration = time.perf_counter() - start
        extra["duration"] = process_duration
        logger.info("",extra=extra)
        return response

    def process_exception(self, request, exception):
        extra = self.__extract_request_info(request)
        logger.opt(exception=exception).bind(extra=extra).error(exception)
        return None
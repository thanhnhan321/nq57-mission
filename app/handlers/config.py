from ..models import SystemConfig
from ..utils.cache import cached

CONFIG_KEY = "config"
# @cached(key=CONFIG_KEY, ttl=60 * 60 * 24)
def get_config(key: SystemConfig.Key) -> str:
    return SystemConfig.objects.filter(key=key).first().value
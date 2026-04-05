from ..models import DirectiveLevel
from ..utils.cache import cached

DIRECTIVE_LEVELS_KEY = "directive_level.all"
@cached(key=DIRECTIVE_LEVELS_KEY, ttl=60 * 60 * 24)
def get_all_directive_levels() -> list[DirectiveLevel]:
    return list(DirectiveLevel.objects.all())

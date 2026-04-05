from ..models import Department
from ..utils.cache import cached

DEPARTMENTS_KEY = "department.all"

# @cached(key=DEPARTMENTS_KEY, ttl=60 * 60 * 24)
def get_all_departments() -> list[Department]:
    return Department.objects.all()

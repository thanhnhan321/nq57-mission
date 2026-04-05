from django.db import models
import uuid

from .base import AuditModel

class Storage(AuditModel):
    object_uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    file_name = models.CharField(max_length=255)
    size = models.BigIntegerField()

    class Meta:
        db_table = 'storage'

    def __str__(self):
        return self.file_name

    @property
    def file_extension(self):
        return self.file_name.rsplit('.', 1)[-1] if '.' in self.file_name else None
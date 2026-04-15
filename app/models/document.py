from django.db import models

from .base import AuditModel
from .storage import Storage
from .period import Period


class DocumentType(AuditModel):
    code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "document_type"

    def __str__(self):
        return self.name


class DirectiveLevel(AuditModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "directive_level"

    def __str__(self):
        return self.name


class DirectiveDocument(AuditModel):
    code = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=255)
    type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="directive_documents",
        db_column="type_code",
    )
    directive_level = models.ForeignKey(
        DirectiveLevel,
        on_delete=models.PROTECT,
        related_name="directive_documents",
    )
    issued_at = models.DateField()
    valid_from = models.DateField()
    valid_to = models.DateField(null=True)
    object = models.ForeignKey(
        Storage,
        on_delete=models.PROTECT,
        related_name="directive_documents",
    )

    class Meta:
        db_table = "directive_document"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.code} - {self.title}"


class Document(AuditModel):
    code = models.CharField(max_length=50, primary_key=True)
    title = models.CharField(max_length=255)
    type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="documents",
        db_column="type_code",
    )
    issued_at = models.DateField()
    issued_by = models.TextField()
    expired_at = models.DateField(null=True)
    object = models.ForeignKey(
        Storage,
        on_delete=models.PROTECT,
        related_name="documents",
    )

    period = models.ForeignKey(
        Period,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='period_document'
    )

    class Meta:
        db_table = "document"
        ordering = ["-issued_at"]
        permissions = [
            ("read_document", "Can read document"),
        ]

    def __str__(self):
        return f"{self.code} - {self.title}"

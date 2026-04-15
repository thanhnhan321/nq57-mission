from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Ranking(models.Model):
    code = models.CharField("Xếp loại", max_length=10, unique=True)
    name = models.CharField("Tên xếp loại", max_length=100)

    score_from = models.FloatField(
        "Điểm từ",
        validators=[MinValueValidator(0)],
    )
    score_to = models.FloatField(
        "Điểm đến",
        validators=[MinValueValidator(0)],
    )

    description = models.CharField("Mô tả", max_length=255, blank=True)

    is_active = models.BooleanField("Đang sử dụng", default=True)

    created_at = models.DateTimeField("Ngày tạo", auto_now_add=True)
    updated_at = models.DateTimeField("Ngày cập nhật", auto_now=True)

    class Meta:
        db_table = "rank"
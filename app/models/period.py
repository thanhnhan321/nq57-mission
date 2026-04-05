from django.db import models

class Period(models.Model):
    year = models.PositiveSmallIntegerField(db_index=True)
    month = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "period"
        constraints = [
            models.UniqueConstraint(
                fields=["year", "month"],
                name="uq_year_month"
            )
        ]
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.year}-{self.month}"
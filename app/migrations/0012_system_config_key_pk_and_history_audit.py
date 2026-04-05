from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0011_system_config"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="systemconfig",
            name="id",
        ),
        migrations.AlterField(
            model_name="systemconfig",
            name="key",
            field=models.TextField(
                choices=[
                    ("mission_cutoff_day", "Nhiệm vụ - ngày chốt hàng tháng"),
                    ("mission_cutoff_time", "Nhiệm vụ - giờ chốt"),
                    ("mission_lock_after_deadline", "Nhiệm vụ - tự động khóa"),
                    ("mission_remind_before_days", "Nhiệm vụ - nhắc nhở nộp"),
                    ("quota_cutoff_day", "Chỉ tiêu - ngày chốt hàng tháng"),
                    ("quota_cutoff_time", "Chỉ tiêu - giờ chốt"),
                    ("quota_lock_after_deadline", "Chỉ tiêu - tự động khóa"),
                    ("quota_remind_before_days", "Chỉ tiêu - nhắc nhở nộp"),
                    ("report_cutoff_day", "Báo cáo - ngày chốt hàng tháng"),
                    ("report_cutoff_time", "Báo cáo - giờ chốt"),
                    ("report_remind_before_days", "Báo cáo - nhắc nhở nộp"),
                ],
                primary_key=True,
                serialize=False,
            ),
        ),
        migrations.AlterModelOptions(
            name="systemconfighistory",
            options={"db_table": "system_config_history", "ordering": ["-created_at", "-id"]},
        ),
        migrations.AddField(
            model_name="systemconfighistory",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="systemconfighistory",
            name="created_by",
            field=models.CharField(default="system", max_length=512),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="systemconfighistory",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="systemconfighistory",
            name="updated_by",
            field=models.CharField(default="system", max_length=512),
            preserve_default=False,
        ),
    ]

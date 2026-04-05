from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_departmentreport_period_document_period_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.TextField(choices=[('mission_cutoff_day', 'Nhiệm vụ - ngày chốt hàng tháng'), ('mission_cutoff_time', 'Nhiệm vụ - giờ chốt'), ('mission_lock_after_deadline', 'Nhiệm vụ - tự động khóa'), ('mission_remind_before_days', 'Nhiệm vụ - nhắc nhở nộp'), ('quota_cutoff_day', 'Chỉ tiêu - ngày chốt hàng tháng'), ('quota_cutoff_time', 'Chỉ tiêu - giờ chốt'), ('quota_lock_after_deadline', 'Chỉ tiêu - tự động khóa'), ('quota_remind_before_days', 'Chỉ tiêu - nhắc nhở nộp'), ('report_cutoff_day', 'Báo cáo - ngày chốt hàng tháng'), ('report_cutoff_time', 'Báo cáo - giờ chốt'), ('report_remind_before_days', 'Báo cáo - nhắc nhở nộp')], unique=True)),
                ('value', models.TextField()),
            ],
            options={
                'db_table': 'system_config',
                'ordering': ['key'],
            },
        ),
        migrations.CreateModel(
            name='SystemConfigHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.TextField(choices=[('mission_cutoff_day', 'Nhiệm vụ - ngày chốt hàng tháng'), ('mission_cutoff_time', 'Nhiệm vụ - giờ chốt'), ('mission_lock_after_deadline', 'Nhiệm vụ - tự động khóa'), ('mission_remind_before_days', 'Nhiệm vụ - nhắc nhở nộp'), ('quota_cutoff_day', 'Chỉ tiêu - ngày chốt hàng tháng'), ('quota_cutoff_time', 'Chỉ tiêu - giờ chốt'), ('quota_lock_after_deadline', 'Chỉ tiêu - tự động khóa'), ('quota_remind_before_days', 'Chỉ tiêu - nhắc nhở nộp'), ('report_cutoff_day', 'Báo cáo - ngày chốt hàng tháng'), ('report_cutoff_time', 'Báo cáo - giờ chốt'), ('report_remind_before_days', 'Báo cáo - nhắc nhở nộp')])),
                ('value', models.TextField()),
            ],
            options={
                'db_table': 'system_config_history',
                'ordering': ['id'],
            },
        ),
    ]

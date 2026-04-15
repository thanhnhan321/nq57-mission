chạy tạo migrate:

```
python manage.py makemigrations app
```
chạy migrate:
```
python manage.py migrate
```

chạy tạo superuser:
```
python manage.py createsuperuser
```

chạy migration:
```
python manage.py migrate app 0011
python manage.py loaddata report_seed.json
```

Kịch bản đúng cho DB mới hoàn toàn là:
1. Đảm bảo app đang trỏ đúng DB trống.
2. Chạy: `python manage.py migrate`
3. Khởi tạo dữ liệu: `python manage.py init_system --noinput`
4. Tạo tài khoản quản trị: `python manage.py createsuperuser`
5. Đồng bộ superuser vào group Member: `python manage.py sync_member_group`
6. (Tùy chọn) Chạy: `python manage.py import_departments_from_csv` (nếu có file app\fixtures\department.csv)

Nếu muốn reset lại dữ liệu bootstrap mà không xoá toàn bộ database:
1. Chạy: `python manage.py init_system --reset --noinput`
2. Hoặc: `python manage.py reset_and_seed_data --noinput`

Ghi chú:
- `init_system` sẽ seed group `Member`, toàn bộ permission hiện có trong app, danh sách kỳ báo cáo từ `app\\fixtures\\reportmonth.json`, và cấu hình hệ thống từ `app\\fixtures\\system_config_sample.json`.
- Sau khi tạo superuser bằng `createsuperuser`, hãy chạy `sync_member_group` để gắn user đó vào group `Member`.
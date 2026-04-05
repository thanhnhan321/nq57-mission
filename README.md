# NQ57 CATP

## Local setup hiện tại

Project đã được chỉnh để local dễ chạy hơn với Docker cho phần hạ tầng:

- PostgreSQL chạy qua `docker compose`
- MinIO chạy qua `docker compose`
- app local dùng:
  - PostgreSQL: `localhost:5435`
  - MinIO API: `localhost:9000`
  - MinIO console: `localhost:9001`
  - bucket: `nghiquyet57`

## Các chỗ đã thay đổi

- [docker-compose.yml](/d:/company/projects/nq57-catp/docker-compose.yml)
  - thêm service `postgres`
  - đổi `minio` sang image public
  - tự tạo bucket `nghiquyet57`
  - bỏ phụ thuộc bắt buộc vào image nội bộ để local dễ dựng

- [.env](/d:/company/projects/nq57-catp/.env)
  - `DB_URL` đổi sang `localhost:5435`
  - `MINIO_CONFIG` đổi sang MinIO local
  - thêm `ENV`, `CONTEXT_ROOT`, `LOG_DIR`

- [.env.example](/d:/company/projects/nq57-catp/.env.example)
  - đồng bộ theo local stack mới

- [app/fixtures/directive_document_sample.json](/d:/company/projects/nq57-catp/app/fixtures/directive_document_sample.json)
  - bỏ field `issued_by` vì không còn khớp model hiện tại

## Chạy project từ đầu

### 1. Dựng hạ tầng local

```powershell
docker compose up -d
```

### 2. Chạy migrate

```powershell
python manage.py migrate
```

### 3. Seed dữ liệu nền

```powershell
python manage.py shell -c "from django.contrib.auth.models import User; u, _ = User.objects.get_or_create(username='root', defaults={'email':'root@example.com','is_staff':True,'is_superuser':True}); u.is_staff=True; u.is_superuser=True; u.is_active=True; u.set_password('123456'); u.save(); print('root-ready')"

python manage.py loaddata app/fixtures/reportmonth.json app/fixtures/directive_level.json app/fixtures/department_sample.json app/fixtures/system_config_sample.json app/fixtures/directive_document_sample.json app/fixtures/document_sample.json

python manage.py shell -c "from app.models import Period; from django.utils import timezone; now=timezone.localtime(); Period.objects.get_or_create(year=now.year, month=now.month); print('period-ready')"
```

### 4. Chạy app

```powershell
python manage.py runserver
```

Mở:

- `http://127.0.0.1:8000/app/`
- `http://127.0.0.1:8000/app/sign-in/`

## Tài khoản local mặc định

- username: `root`
- password: `123456`

## Cấu trúc dự án

Dự án là một ứng dụng Django, dùng PostgreSQL để lưu dữ liệu nghiệp vụ và MinIO để lưu file đính kèm.

### Thư mục gốc

- `app/`: app nghiệp vụ chính của hệ thống.
- `core/`: cấu hình Django ở mức project, gồm settings, URL gốc, middleware, Jinja2.
- `static/`: tài nguyên frontend dùng chung như CSS, JS, icon, template file import/export.
- `utils/`: các hàm tiện ích dùng chung toàn hệ thống như log, JSON, MinIO, exception.
- `logs/`: nơi ghi log runtime khi chạy local.
- `.agents/`: cấu hình/skill nội bộ phục vụ agent, không ảnh hưởng logic chạy app.

### Các file cấu hình chính

- `manage.py`: điểm vào cho các lệnh Django như `runserver`, `migrate`, `loaddata`.
- `env.py`: đọc và parse biến môi trường từ `.env`.
- `.env`: cấu hình môi trường local hiện tại.
- `.env.example`, `env.example`: mẫu cấu hình môi trường.
- `requirements.txt`: danh sách thư viện Python cần cài.
- `docker-compose.yml`: dựng hạ tầng local như PostgreSQL và MinIO.
- `Dockerfile`: build image chạy ứng dụng.
- `README.md`: hướng dẫn setup và chạy dự án.

### Bên trong `core/`

- `core/settings.py`: cấu hình chính của Django, database, static, cache, Huey worker.
- `core/urls.py`: route gốc của toàn project.
- `core/jinja2.py`: cấu hình template engine Jinja2.
- `core/middlewares/`: middleware tự viết, chủ yếu cho log và message.
- `core/asgi.py`, `core/wsgi.py`: entrypoint khi deploy.

### Bên trong `app/`

- `app/models/`: khai báo model dữ liệu.
  - `department.py`: phòng ban và hồ sơ người dùng.
  - `document.py`: văn bản, văn bản chỉ đạo, loại văn bản, cấp chỉ đạo.
  - `quota.py`: chỉ tiêu và báo cáo chỉ tiêu.
  - `mission.py`: nhiệm vụ và báo cáo nhiệm vụ.
  - `department_report.py`: báo cáo tổng hợp theo đơn vị.
  - `period.py`: kỳ báo cáo theo tháng/năm.
  - `storage.py`: metadata file đã upload.
  - `system_config.py`: cấu hình hệ thống và lịch sử thay đổi.
  - `notification.py`, `report.py`: các model hỗ trợ khác.
- `app/views/`: xử lý giao diện và endpoint theo từng module nghiệp vụ.
  - `dashboard/`: dashboard nội bộ.
  - `document/`: quản lý văn bản.
  - `directive_document/`: quản lý văn bản chỉ đạo.
  - `mission/`: quản lý nhiệm vụ.
  - `quota/`: quản lý chỉ tiêu.
  - `report/`: báo cáo.
  - `profile/`: thông tin người dùng.
  - `system/`: quản trị hệ thống như người dùng, cấu hình, phòng ban.
  - `categories/`: danh mục dùng chung.
  - `options/`: API trả option cho dropdown/filter.
  - `public/`: các màn hình/route công khai.
  - `templates/`: layout và component template dùng lại.
  - `ui_showcase/`: khu vực demo giao diện/components.
- `app/handlers/`: logic hỗ trợ cho một số nghiệp vụ hoặc dữ liệu chọn lọc.
- `app/tasks/`: background task chạy qua Huey.
- `app/fixtures/`: dữ liệu mẫu để seed local/dev.
- `app/migrations/`: lịch sử migration database.
- `app/utils/`: helper riêng cho app.
- `app/apps.py`: cấu hình Django app.
- `app/constants.py`: hằng số dùng chung.
- `app/admin.py`: đăng ký model cho Django admin.

### Dữ liệu được lưu ở đâu

- Dữ liệu nghiệp vụ: PostgreSQL.
- File đính kèm: MinIO.
- Metadata file upload: bảng `storage` trong database.

## Lưu ý

- DB local cũ ở cổng `5434` đã từng bị lệch migration; local stack mới dùng cổng `5435`
- nếu lỗi schema lạ quay lại, cách nhanh nhất là:
  1. `docker compose down -v`
  2. `docker compose up -d`
  3. chạy lại `migrate` và seed dữ liệu nền

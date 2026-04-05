import re


USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_.]+$')
PHONE_PATTERN = re.compile(r'^\d+$')


def validate_username(username):
    if not username:
        return 'Tên đăng nhập là bắt buộc'
    if len(username) < 3 or len(username) > 30:
        return 'Tên đăng nhập phải từ 3 đến 30 ký tự'
    if any(character.isspace() for character in username):
        return 'Tên đăng nhập không được chứa khoảng trắng'
    if not USERNAME_PATTERN.fullmatch(username):
        return 'Tên đăng nhập chỉ được chứa chữ, số, dấu chấm và dấu gạch dưới'
    return None


def validate_phone(phone):
    if not phone:
        return 'Số điện thoại là bắt buộc'
    if not PHONE_PATTERN.fullmatch(phone):
        return 'Số điện thoại chỉ được chứa chữ số'
    if len(phone) < 8 or len(phone) > 15:
        return 'Số điện thoại phải từ 8 đến 15 chữ số'
    return None


def validate_password(password):
    if len(password) < 8:
        return 'Mật khẩu phải có ít nhất 8 ký tự'
    if not any(character.isupper() for character in password):
        return 'Mật khẩu phải có ít nhất một chữ hoa'
    if not any(character.isdigit() for character in password):
        return 'Mật khẩu phải có ít nhất một số'
    return None

from ....constants import OPTION_COLOR_CLASS_MAP


def role_badge_formatter(value):
    color = 'blue' if value == 'Quản trị viên' else 'gray'
    badge = f'<div class="w-fit rounded-full {OPTION_COLOR_CLASS_MAP[color]} text-xs px-2 py-1">{value}</div>'
    return f'<div class="flex justify-center w-full">{badge}</div>'


def status_badge_formatter(value):
    text = 'Hoạt động' if value else 'Tạm khóa'
    color = 'green' if value else 'red'
    badge = f'<div class="w-fit rounded-full {OPTION_COLOR_CLASS_MAP[color]} text-xs px-2 py-1">{text}</div>'
    return f'<div class="flex justify-center w-full">{badge}</div>'


def department_formatter(value):
    return f'<div class="flex justify-center w-full">{value}</div>'

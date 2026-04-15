from django.utils.html import format_html

def render_rank_badge(code: str):
    badge_styles = {
        'A': {'bg': '#DCFCE7', 'text': '#15803D'},
        'B': {'bg': '#DBEAFE', 'text': '#1D4ED8'},
        'C': {'bg': '#FEF3C7', 'text': '#A16207'},
        'D': {'bg': '#FFEDD5', 'text': '#C2410C'},
        'E': {'bg': '#FEE2E2', 'text': '#BE123C'},
    }

    code = (code or '').strip().upper()
    style = badge_styles.get(code, {'bg': '#F1F5F9', 'text': '#334155'})

    return format_html(
        '<span style="background:{}; color:{}; padding:6px 12px; border-radius:8px; font-weight:600; display:inline-block; min-width:32px; text-align:center;">{}</span>',
        style['bg'],
        style['text'],
        code
    )
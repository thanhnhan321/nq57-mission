from enum import StrEnum
from pydantic import BaseModel, model_validator

class Button(BaseModel):
    class IconPosition(StrEnum):
        LEFT = 'left'
        RIGHT = 'right'
    
    class Variant(StrEnum):
        FILLED = 'filled'
        OUTLINED = 'outlined'
        TRANSPARENT = 'transparent'

    label: str | None = None
    icon: str | None = None
    icon_position: IconPosition = IconPosition.LEFT
    variant: Variant = Variant.FILLED
    disabled: bool = False
    loading_text: str = 'Đang xử lý...'
    href: str | None = None
    htmx_event_prefix: str | None = None
    klass: str = ''
    extra_attributes: dict = {}

    @model_validator(mode='after')
    def check_empty(self) -> bool:
        if not self.label and not self.icon:
            raise ValueError('Label or icon is required')
        return self
    
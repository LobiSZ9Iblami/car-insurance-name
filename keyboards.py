from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_insurance_confirmation_keyboard(include_restart: bool = True) -> InlineKeyboardBuilder:

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Confirming the purchase of auto insurance", callback_data="confirm_car_insurance")
    if include_restart:
        keyboard.button(text="Don't agree with the price of insurance, find another one", callback_data="reject_car_insurance")
    keyboard.button(text="Abort the process", callback_data="exit")
    keyboard.adjust(1, 1, 1)

    return keyboard


def get_doc_confirmation_keyboard() -> InlineKeyboardBuilder:

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Yeah, that's right.", callback_data="confirm_doc")
    keyboard.button(text="🔁 No, send it again", callback_data="restart_doc")
    keyboard.button(text="Abort the process", callback_data="exit")
    keyboard.adjust(1, 1, 1)

    return keyboard



def start_OCR() -> InlineKeyboardBuilder:

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📤 Retrieve Data", callback_data="confirm_docs")
    keyboard.adjust(1)

    return keyboard
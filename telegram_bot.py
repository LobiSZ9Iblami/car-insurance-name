import aiogram
import asyncio
import tempfile
from pathlib import Path
import json

from io import BytesIO

from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

from bot_config import bot_key
from price_calculation import get_insurance_price, get_insurance_price_all
from keyboards import get_insurance_confirmation_keyboard, get_doc_confirmation_keyboard, start_OCR
from bot_AI import ask_cohere_labs
from mindee_doc_model import extreact_value, extract_words_from_image, get_name, get_car_plate_num

bot = aiogram.Bot(token = bot_key)
storage = MemoryStorage()
dp = aiogram.Dispatcher(storage = storage)

class DocumentsState(StatesGroup):
    await_for_passport = State()
    await_for_vehicle_id = State()
    manual_input = State()
    await_for_user_data_agreement = State()


@dp.message(CommandStart())
async def bot_start_work(message: Message, state: FSMContext):
        # await message.answer(
        #     "Hello, I am Car Insurance Bot, I will help you buy car insurance. \n"
        #     "Send me your passport and vehicle identification document, and I'll do the paperwork."
        # )
        # await state.set_state(DocumentsState.await_for_passport)

        '''AI part'''
        greeting_text = await ask_cohere_labs("Say hello to a user who wants to buy insurance."
                                          "And tell them that to buy insurance you expect a photo of passport and technical passport (car document)."
                                                "Ask to send a passport photo firstly.")

        await message.answer(greeting_text, parse_mode="MarkdownV2")

        await state.set_state(DocumentsState.await_for_passport)


@dp.message(aiogram.F.photo, DocumentsState.await_for_passport)
async def get_passport(message: Message, state: FSMContext):

    passport_photo = await bot.get_file(message.photo[-1].file_id)
    photo_bytes = await bot.download_file(passport_photo.file_path)
    photo_bytes = BytesIO(photo_bytes.read())

    await state.update_data(passport_photo = photo_bytes)

    # await message.answer(f"✅ Паспорт получен. Теперь, пожалуйста, отправь фото документа на автомобиль.")

    receive_passport = await ask_cohere_labs("Say thank you, tell them that the passport has been received and ask user to send a photo of the car document so that you can see the license plate number of the vehicle")
    print(receive_passport)
    await message.answer(receive_passport, parse_mode="MarkdownV2")

    await state.set_state(DocumentsState.await_for_vehicle_id)


@dp.message(aiogram.F.photo, DocumentsState.await_for_vehicle_id)
async def get_vehicle_id(message: Message, state: FSMContext):

    vehicle_id_photo = await bot.get_file(message.photo[-1].file_id)
    photo_bytes = await bot.download_file(vehicle_id_photo.file_path)
    photo_bytes = BytesIO(photo_bytes.read())

    await state.update_data(vehicle_id_photo = photo_bytes)

    receive_car_id = await ask_cohere_labs("inform the user that both documents have been received and ask the user to click the Retrieve Data button to read the necessary information from the photos to register the policy..")
    print(receive_car_id)
    keyboard = start_OCR()
    await message.answer(
        text=receive_car_id,
        # f"✅ Отлично! Оба документа получены. Теперь распознаю данные...",
        reply_markup = keyboard.as_markup(),
        parse_mode = "MarkdownV2"
    )

    await state.set_state(DocumentsState.await_for_user_data_agreement)


@dp.callback_query(aiogram.F.data == "confirm_docs")
async def confirm_docs(callback: aiogram.types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("📤 Extracting data from documents...")


    get_photo_data = await state.get_data()
    passport_photo_bytes = get_photo_data['passport_photo']
    passport_photo_bytes.seek(0)


    # user_name = asyncio.to_thread(photo_preparation, passport_photo_bytes, get_name)
    user_name = await photo_preparation(passport_photo_bytes, get_name)

    car_plate_bytes = get_photo_data['vehicle_id_photo']
    car_plate_bytes.seek(0)

    # plate_number = asyncio.to_thread(photo_preparation, car_plate_bytes, get_car_plate_num)
    plate_number = await photo_preparation(car_plate_bytes, get_car_plate_num)

    update_extracted_data = await state.get_data()
    extracted = update_extracted_data.get("extracted", {})
    extracted.update(
        {
            "user_name": user_name,
            "plate_number": plate_number
        }
    )
    await state.update_data(extracted = extracted)

    extracted_data_user_check = (
        f"Here's what I was able to recognize from the documents:\n\n"
        f"👤 Your name: {user_name}\n"
        f"🚗 Plate number: {plate_number}\n"
        f"Is that correct?"
    )

    keyboard = get_doc_confirmation_keyboard()
    await callback.message.answer(text=extracted_data_user_check, reply_markup=keyboard.as_markup(), parse_mode="MarkdownV2")


async def photo_preparation(photo_bytes, function):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
        tmp_file.write(photo_bytes.read())
        temp_path = Path(tmp_file.name)

    try:
        # Распознаём
        result_json_str = await asyncio.to_thread(extract_words_from_image, str(temp_path))
        result_json = json.loads(result_json_str)

        # Извлекаем значения
        extracted_data_raw = await asyncio.to_thread(extreact_value, result_json, "value")
        extracted_data = await asyncio.to_thread(function, extracted_data_raw)

        return extracted_data

    finally:
        temp_path.unlink(missing_ok=True)

@dp.callback_query(aiogram.F.data == "restart_doc")
async def restart_docs(callback: aiogram.types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(DocumentsState.await_for_passport)
    await callback.message.answer(
        "🔄 Let's start over!\n"
        "Please send a passport photo 📄."
    )



@dp.callback_query(aiogram.F.data == "confirm_doc")
async def set_a_price(callback: aiogram.types.CallbackQuery, state: FSMContext):

    await callback.answer()

    insurance_data = await get_insurance_price()
    insurance_company, price = list(insurance_data.items())[0]

    update_extracted_data = await state.get_data()
    extracted = update_extracted_data.get("extracted", {})
    extracted.update(
        {
            'price': price,
            'insurance_company': insurance_company
        }
    )
    await state.update_data(extracted = extracted)

    keyboard = get_insurance_confirmation_keyboard(include_restart = True)
    # await callback.message.answer(f"Price of the car insurance is - {price} USD company is - {insurance_company}.\n"
    #                               f"Do you agree to proceed?", reply_markup=keyboard.as_markup())

    user_price_check = await ask_cohere_labs(f"Say you've done the calculations and can recommend a policy from the company - {insurance_company}, with a price - {price} in USD")
    await callback.message.answer(user_price_check, reply_markup=keyboard.as_markup(), parse_mode="MarkdownV2")


@dp.callback_query(aiogram.F.data == "reject_car_insurance")
async def user_price_insurance_disagree(callback: aiogram.types.CallbackQuery, state: FSMContext):
    await callback.answer()

    insurance_data = await get_insurance_price()
    insurance_company, price = list(insurance_data.items())[0]

    keyboard = get_insurance_confirmation_keyboard(include_restart = False)
    # await callback.message.answer(f"I am sorry but {price} USD is the only available price.\n"
    #                               f"Do you agree to proceed?", reply_markup=keyboard.as_markup())

    user_price_check_disagree = await ask_cohere_labs(f"Apologize and say it's the only policy available and only at that price point")
    await callback.message.answer(text = user_price_check_disagree, reply_markup = keyboard.as_markup(), parse_mode="MarkdownV2")


@dp.callback_query(aiogram.F.data == "confirm_car_insurance")
async def user_price_insurance_agree(callback: aiogram.types.CallbackQuery, state: FSMContext):
    await callback.answer()

    # print("Button 'Подтверждаю покупку автостраховки' clicked")
    insurance_data = await state.get_data()
    # print(insurance_data)
    # await callback.message.answer(f"Страховой полис:\n\n"
    #                               f"На - {insurance_data['extracted']['user_name']} \n"
    #                               f"Машина - {insurance_data['extracted']['plate_number']}\n"
    #                               f"Страховая - {insurance_data['extracted']['insurance_company']}\n"
    #                               f"Цена - {insurance_data['extracted']['price']}")

    insurance_text = await generate_insurance(insurance_data)
    await callback.message.answer(text = insurance_text, parse_mode="MarkdownV2")


async def generate_insurance(insurance_data: dict) -> dict:
    prompt = (
        f"Based on the following data, generate the text of an insurance policy:\n"
        f"lastname and firstname: {insurance_data['extracted']['user_name']}\n"
        f"plate number: {insurance_data['extracted']['plate_number']}\n"
        f"insurance company: {insurance_data['extracted']['insurance_company']}\n"
        f"insurance price: {insurance_data['extracted']['price']} USD\n\n"
        "Generate random Policy Number"
        "As Effective Date use today"
        "As Expiration Date use today + one year"
        "The policy should be formalized but in a friendly manner."
    )

    insurance_text = await ask_cohere_labs(prompt = prompt, parse_mode="MarkdownV2")
    return insurance_text

@dp.callback_query(aiogram.F.data == "exit")
async def close_the_process(callback: aiogram.types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.answer("The process were aborted. Come again. Thx.")

@dp.message(Command("exit"))
async def close_the_process(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("The process were aborted. Come again. Thx.")

@dp.message(Command("status"))
async def user_status_handler(message: Message, state: FSMContext):
    current_user_state = await state.get_state()

    if current_user_state is None:
        await message.answer("Press /start command, you are not at any statuses.")
    elif current_user_state == DocumentsState.await_for_passport.state:
        await message.answer("📄 Awaiting passport photo.")
    elif current_user_state == DocumentsState.await_for_vehicle_id.state:
        await message.answer("🚗 Awaiting a photo of the vehicle document.")
    elif current_user_state == DocumentsState.await_for_user_data_agreement:
        await message.answer("✅ Await for user data agreement")
    else:
        await message.answer(f"⚙️ Current Status: {current_user_state}")



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

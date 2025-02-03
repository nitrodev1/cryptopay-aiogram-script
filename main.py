import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
import aiohttp
import asyncio

TELEGRAM_TOKEN = ''
CRYPTOPAY_API_TOKEN = ''


logging.basicConfig(level=logging.INFO)


bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
router = Router()  


invoices = {}


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="invoice", description="Создать счет"),
    ]
    await bot.set_my_commands(commands)


@router.message(Command("start"))
async def send_welcome(message):
    await message.answer("Привет! Я бот для работы с Crypto Pay. Используйте команду /invoice для создания счета.")


@router.message(Command("invoice"))
async def create_invoice(message):
    amount = 1.0  # Amount to pay
    currency = 'USDT'  # Currency
    description = 'Payment for the service.'

    invoice = await create_crypto_invoice(amount, currency, description)
    if invoice:
        pay_url = invoice.get('pay_url')
        invoice_id = invoice.get('invoice_id')
        invoices[invoice_id] = invoice  
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Проверить оплату", callback_data=f"check_payment:{invoice_id}")]
            ]
        )
        await message.answer(f"Счет создан! Оплатите по ссылке: {pay_url}", reply_markup=keyboard)
    else:
        await message.answer("Не удалось создать счет. Попробуйте позже.")


async def create_crypto_invoice(amount, currency, description):
    url = 'https://testnet-pay.crypt.bot/api/createInvoice'
    headers = {
        'Crypto-Pay-API-Token': CRYPTOPAY_API_TOKEN,
        'Content-Type': 'application/json'
    }
    payload = {
        'asset': currency,
        'amount': amount,
        'description': description
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            response_text = await response.text()
            logging.info(f"Запрос: {payload}")
            logging.info(f"Ответ: {response_text}")
            if response.status == 200:
                result = await response.json()
                if result.get('ok'):
                    return result.get('result')
            logging.error(f"Ошибка при создании счета: {response.status}")
    return None


@router.callback_query(F.data.startswith('check_payment'))
async def check_payment_status(callback: CallbackQuery):
    invoice_id = callback.data.split(":")[1]
    invoice = invoices.get(int(invoice_id))
    if invoice:
        status = await get_payment_status(invoice_id)
        if not status:
            await callback.message.answer("Не удалось получить статус оплаты.")
            return

        ispaid = True if status == 'paid' else False
        await callback.message.answer(f"Статус оплаты: {'оплата произведена' if ispaid else 'оплаты нет'}")
    else:
        await callback.message.answer("Счет не найден.")


async def get_payment_status(invoice_id):
    url = 'https://testnet-pay.crypt.bot/api/getInvoices'
    headers = {
        'Crypto-Pay-API-Token': CRYPTOPAY_API_TOKEN
    }
    payload = {
        'invoice_ids': invoice_id
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            response_text = await response.text()
            logging.info(f"Запрос: {payload}")
            logging.info(f"Ответ: {response_text}")
            if response.status == 200:
                result = await response.json()
                if result.get('ok'):
                    invoices = result.get('result', [])
                    if invoices:
                        item = next(iter(invoices['items']), None)
                        return item.get('status')
            logging.error(f"Ошибка при получении статуса счета: {response.status}")
    return None


async def main():
    await set_commands(bot)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
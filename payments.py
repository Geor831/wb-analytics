from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uuid
import os

app = FastAPI()

# Разрешаем запросы с вашего сайта (GitHub Pages)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://geor831.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ВАШИ ДАННЫЕ ИЗ ЮKASSA =====
SHOP_ID = "1424260"
SECRET_KEY = "live_DKnYmtqP_Km9H8nIxZvD7BeI1C1JW9TqmKgJmiT-Db8"
# ==================================

@app.post("/create-payment")
async def create_payment(request: Request):
    data = await request.json()
    amount = data.get("amount")       # 490, 990, 2490
    tariff = data.get("tariff")       # "Старт", "Про", "Бизнес"

    if not amount or not tariff:
        raise HTTPException(status_code=400, detail="Не указана сумма или тариф")

    idempotence_key = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.yookassa.ru/v3/payments",
            json={
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://geor831.github.io/wb-analytics/success.html"
                },
                "capture": True,
                "description": f"Тариф {tariff} — WB.Analytics",
                "metadata": {
                    "tariff": tariff,
                    "user_login": "anonymous"  # можно заменить на текущего пользователя
                }
            },
            auth=(SHOP_ID, SECRET_KEY),
            headers={"Idempotence-Key": idempotence_key}
        )

    if response.status_code != 200:
        error_text = await response.aread()
        raise HTTPException(status_code=400, detail=f"Ошибка ЮKassa: {error_text}")

    payment_data = response.json()
    return {
        "payment_id": payment_data["id"],
        "confirmation_url": payment_data["confirmation"]["confirmation_url"]
    }

@app.post("/yookassa-webhook")
async def webhook(request: Request):
    event = await request.json()
    if event.get("event") == "payment.succeeded":
        payment_id = event["object"]["id"]
        metadata = event["object"].get("metadata", {})
        tariff = metadata.get("tariff")
        # Здесь можно активировать тариф пользователю
        print(f"✅ Оплачен тариф: {tariff}, ID платежа: {payment_id}")
        # Отправить уведомление в Telegram (опционально)
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "Payment server is running"}
class Config:
    API_ID = 0000000
    API_HASH = ""
    TOKEN = ""
    TEST_TOKEN = ""
    DATABASE_URI = "postgresql+asyncpg://postgres:admin@localhost/a2z"
    REPORT_CHANNEL_ID: int = -1000000000 # Channel ID of where reports are go
    DAILY_CHAT_LIMIT = 20
    ADMIN_ID: int = 00000000 # Admin/Owner ID
    PREMIUM_CHANNEL_ID: int = -10000000 # Channel ID of where notification of premium subscription goes
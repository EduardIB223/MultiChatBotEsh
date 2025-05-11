# TopicCreateBot

A Telegram bot that creates forum chats with topics using both Aiogram and Telethon.

## Project Structure

```
TopicCreateBot/
├── main.py              # Main entry point
├── config.py            # Configuration and tokens
├── handlers/            # Command handlers
│   ├── commands.py     # Basic commands
│   └── admin.py        # Admin commands
├── services/           # Services
│   ├── telethon.py    # Telethon logic
│   └── database.py    # Database operations
├── models/            # Data models
│   └── schemas.py     # Pydantic schemas
└── utils/             # Utilities
    └── validators.py  # Validators
```

## Setup

1. Create a `.env` file with the following variables:
```
BOT_TOKEN=your_aiogram_bot_token
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
PHONE=your_phone_number
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the bot:
```bash
python main.py
```

## Features

- Create forum chats with topics
- Manage templates for chat creation
- JSON-based configuration
- User-friendly interface via Aiogram
- Powerful backend operations via Telethon 
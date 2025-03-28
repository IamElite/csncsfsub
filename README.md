# Force Subscribe Bot

A Telegram bot that enforces channel subscription in groups.

## Deploy to Heroku
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/IamElite/csncsfsub)

## Environment Variables

- `BOT_TOKEN` - Get from [@BotFather](https://t.me/BotFather)
- `MONGO_URL` - Your MongoDB connection URL
- `OWNER_ID` - Your Telegram User ID
- `LOGGER_ID` - Channel/Group ID for logs
- `API_ID` - Get from [my.telegram.org](https://my.telegram.org)
- `API_HASH` - Get from [my.telegram.org](https://my.telegram.org)
- `FSUB` - Force Subscribe Channel IDs (Optional)

## Features
- Force subscribe to channels before using bot
- Support for multiple channels (up to 4)
- Admin commands for managing subscriptions
- User stats and analytics
- Broadcast messages to all groups

## Commands
- `/start` - Start the bot
- `/help` - Show help message
- `/setjoin` - Setup force subscription
- `/join` - Enable/Disable force subscription
- `/status` - Check current force subscription status
- `/stats` - View group statistics
- `/broadcast` - Broadcast message (Admin only)
- `/ban` - Ban user from using bot
- `/unban` - Unban user

## Support
For support and queries, contact [your-support-channel](https://t.me/your_support_channel)

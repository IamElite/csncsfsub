# Force Subscribe Bot

A Telegram bot that enforces channel subscription in groups.

<h3 align="center">
    ─「 ᴅᴇᴩʟᴏʏ ᴏɴ ʜᴇʀᴏᴋᴜ 」─
</h3>

<p align="center"><a href="https://dashboard.heroku.com/new?template=https://github.com/IamElite/csncsfsub"> <img src="https://img.shields.io/badge/Deploy%20On%20Heroku-black?style=for-the-badge&logo=heroku" width="220" height="38.45"/></a></p>



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

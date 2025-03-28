import os
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.errors import UserNotParticipantError, ChannelPrivateError
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(DURGESH)

# Environment variables with default values
BOT_TOKEN = os.getenv("BOT_TOKEN", None)
MONGO_URI = os.getenv("MONGO_URL", None)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
LOGGER_ID = int(os.getenv("LOGGER_ID", "0"))
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", None)
FSUB = os.getenv("FSUB", "").strip()  # Add force sub channels/groups

# Parse force sub channels/groups
FSUB_IDS = []
if FSUB:
    try:
        fsub_list = FSUB.split()
        if len(fsub_list) > 4:
            logger.warning("Maximum 4 force subscription channels allowed. Using first 4.")
            fsub_list = fsub_list[:4]
        FSUB_IDS = [int(x) for x in fsub_list]
    except:
        logger.error("Invalid FSUB format. Should be space-separated channel IDs.")

# Add new function to check owner's force sub
async def check_owner_fsub(user_id):
    if not FSUB_IDS or user_id == OWNER_ID:
        return True
        
    missing_subs = []
    for channel_id in FSUB_IDS:
        try:
            await bot(GetParticipantRequest(channel=channel_id, participant=user_id))
        except UserNotParticipantError:
            try:
                channel = await bot.get_entity(channel_id)
                missing_subs.append(channel)
            except:
                continue
    return missing_subs

# Add event handler for all messages
@app.on(events.NewMessage)
async def check_fsub_handler(event):
    if event.is_private and event.raw_text.startswith('/'):
        user_id = event.sender_id
        missing_subs = await check_owner_fsub(user_id)
        
        if missing_subs is True:
            return
            
        if missing_subs:
            buttons = []
            for channel in missing_subs:
                if hasattr(channel, 'username') and channel.username:
                    buttons.append([Button.url(f"Join {channel.title}", f"https://t.me/{channel.username}")])
                else:
                    try:
                        from telethon.tl.functions.messages import ExportChatInviteRequest
                        invite = await bot(ExportChatInviteRequest(channel.id))
                        buttons.append([Button.url(f"Join {channel.title}", invite.link)])
                    except:
                        continue
            
            await event.reply(
                "**⚠️ ᴀᴄᴄᴇss ʀᴇsᴛʀɪᴄᴛᴇᴅ ⚠️**\n\n"
                "**ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ(s) ᴛᴏ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ!**\n"
                "**ᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ᴊᴏɪɴ**\n"
                "**ᴛʜᴇɴ ᴛʀʏ ᴀɢᴀɪɴ!**",
                buttons=buttons
            )
            return True
    return False

# Modify all command handlers to check FSUB first
@app.on(events.NewMessage(pattern="/start"))
async def start_command(event):
    if await check_fsub_handler(event):
        return
    if await is_rate_limited(event.sender_id):
        return await event.reply("**⚠️ Please wait a moment before using commands again!**")
        
    await update_user_stats(event.sender_id, event.sender.username, event.sender.first_name)
    
    if event.is_private:
        me = await bot.get_me()
        await event.reply(
            f"👋 **Hello {event.sender.first_name}!**\n\n"
            f"I am a Force Subscription Bot. Add me to your group and I'll make sure new members join your channel before chatting.\n\n"
            f"**Commands:**\n"
            f"• /setjoin - Setup force subscription (Single/Multiple channels)\n"
            f"• /join - Enable/Disable force subscription\n"
            f"• /status - Check current force subscription status\n"
            f"• /stats - View group statistics\n"
            f"• /broadcast - Broadcast message (Admin only)\n"
            f"• /ban - Ban user from using bot\n"
            f"• /unban - Unban user\n\n"
            f"**Note:** You can add up to 4 channels in multiple mode",
            buttons=[
                [Button.url("➕ Add me to your group", f"https://t.me/{me.username}?startgroup=true")]
            ]
        )
    else:
        await event.reply("I'm alive! Use /help to see available commands.")

# Stats command
@app.on(events.NewMessage(pattern="/stats"))
async def stats_command(event):
    if await check_fsub_handler(event):
        return
    if not event.is_group:
        return
        
    if await is_rate_limited(event.sender_id):
        return await event.reply("**⚠️ Please wait a moment before using commands again!**")

    chat_id = event.chat_id
    user_id = event.sender_id
    
    if not await is_admin(chat_id, user_id) and user_id != OWNER_ID:
        return await event.reply("**🚫 Only admins can use this command!**")
    
    group_data = await groups_collection.find_one({"chat_id": chat_id})
    if not group_data:
        return await event.reply("**❌ No statistics available for this group.**")
    
    total_messages = group_data.get("total_messages", 0)
    active_users = group_data.get("active_users", 0)
    
    await event.reply(
        f"**📊 Group Statistics**\n\n"
        f"**Total Messages:** {total_messages}\n"
        f"**Active Users:** {active_users}\n"
        f"**Force Sub Status:** {'Enabled' if await forcesub_collection.find_one({'chat_id': chat_id}) else 'Disabled'}"
    )

# Broadcast command
@app.on(events.NewMessage(pattern="/broadcast"))
async def broadcast_command(event):
    if event.sender_id != OWNER_ID:
        return
        
    if not event.is_reply:
        return await event.reply("**❌ Please reply to a message to broadcast!**")
    
    message = await event.get_reply_message()
    all_groups = groups_collection.find({})
    
    success = 0
    failed = 0
    
    async for group in all_groups:
        try:
            await bot.send_message(group["chat_id"], message)
            success += 1
        except Exception:
            failed += 1
            
    await event.reply(
        f"**📢 Broadcast Completed**\n\n"
        f"**Success:** {success}\n"
        f"**Failed:** {failed}"
    )

# Ban command
@app.on(events.NewMessage(pattern="/ban"))
async def ban_command(event):
    if event.sender_id != OWNER_ID:
        return
        
    if not event.is_reply and len(event.raw_text.split()) == 1:
        return await event.reply("**❌ Please reply to a user's message or provide a user ID to ban!**")
    
    try:
        if event.is_reply:
            user_id = (await event.get_reply_message()).sender_id
        else:
            user_id = int(event.raw_text.split()[1])
            
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"banned": True}},
            upsert=True
        )
        
        await event.reply(f"**✅ User {user_id} has been banned from using the bot!**")
    except Exception as e:
        await event.reply(f"**❌ Error: {str(e)}**")

# Unban command
@app.on(events.NewMessage(pattern="/unban"))
async def unban_command(event):
    if event.sender_id != OWNER_ID:
        return
        
    if not event.is_reply and len(event.raw_text.split()) == 1:
        return await event.reply("**❌ Please reply to a user's message or provide a user ID to unban!**")
    
    try:
        if event.is_reply:
            user_id = (await event.get_reply_message()).sender_id
        else:
            user_id = int(event.raw_text.split()[1])
            
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"banned": False}}
        )
        
        await event.reply(f"**✅ User {user_id} has been unbanned!**")
    except Exception as e:
        await event.reply(f"**❌ Error: {str(e)}**")

# Help command
@app.on(events.NewMessage(pattern="/help"))
async def help_command(event):
    await event.reply(
        "**📚 Force Subscription Bot Help**\n\n"
        "**Admin Commands:**\n"
        "• /join <channel username or ID> - Set force subscription\n"
        "• /join off - Disable force subscription\n"
        "• /status - Check current force subscription status\n\n"
        "**How to use:**\n"
        "1. Add me to your group as admin\n"
        "2. Add me to your channel as admin with 'Invite Users' permission\n"
        "3. Use /join command in your group to set force subscription"
    )

# Status command
@app.on(events.NewMessage(pattern="/status"))
async def status_command(event):
    if await check_fsub_handler(event):
        return
    if not event.is_group:
        return
        
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check if user is admin
    is_admin = False
    async for admin in app.iter_participants(chat_id, filter=ChannelParticipantAdmin):
        if admin.id == user_id:
            is_admin = True
            break
    
    if not (is_admin or user_id == event.chat.creator or user_id == OWNER_ID):
        return await event.reply("**ᴏɴʟʏ ɢʀᴏᴜᴘ ᴏᴡɴᴇʀs ᴏʀ sᴜᴅᴏᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.**")
    
    forcesub_data = await forcesub_collection.find_one({"chat_id": chat_id})
    if not forcesub_data:
        return await event.reply("**ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ɪs ɴᴏᴛ ᴇɴᴀʙʟᴇᴅ ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ.**")
    
    try:
        channel_id = forcesub_data["channel_id"]
        channel_info = await bot.get_entity(int(channel_id))
        channel_title = channel_info.title
        channel_username = forcesub_data["channel_username"]
        
        await event.reply(
            f"**ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴇɴᴀʙʟᴇᴅ ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ.**\n\n"
            f"**ᴄʜᴀɴɴᴇʟ:** {channel_title}\n"
            f"**ᴄʜᴀɴɴᴇʟ ɪᴅ:** `{channel_id}`"
        )
    except Exception as e:
        await forcesub_collection.delete_one({"chat_id": chat_id})
        await event.reply("**ᴇʀʀᴏʀ: ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴄʜᴀɴɴᴇʟ ɴᴏᴛ ғᴏᴜɴᴅ. ɪᴛ ʜᴀs ʙᴇᴇɴ ᴅɪsᴀʙʟᴇᴅ.**")

# Join command to set force subscription
@app.on(events.NewMessage(pattern=r"[/!\.](join|fsub|forcesub)($| .+)"))
async def set_forcesub(event):
    if not event.is_group:
        return
        
    chat_id = event.chat_id
    user_id = event.sender_id
    
    # Check if user is admin
    is_admin = False
    async for admin in app.iter_participants(chat_id, filter=ChannelParticipantAdmin):
        if admin.id == user_id:
            is_admin = True
            break
    
    if not (is_admin or user_id == event.chat.creator or user_id == OWNER_ID):
        return await event.reply("**ᴏɴʟʏ ɢʀᴏᴜᴘ ᴏᴡɴᴇʀs ᴏʀ sᴜᴅᴏᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ.**")

    args = event.pattern_match.group(2).strip()
    
    if args.lower() in ["off", "disable"]:
        await forcesub_collection.delete_one({"chat_id": chat_id})
        return await event.reply("**ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʜᴀs ʙᴇᴇɴ ᴅɪsᴀʙʟᴇᴅ ғᴏʀ ᴛʜɪs ɢʀᴏᴜᴘ.**")

    if not args:
        return await event.reply("**ᴜsᴀɢᴇ: /join <ᴄʜᴀɴɴᴇʟ ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ɪᴅ> ᴏʀ /join ᴏғғ ᴛᴏ ᴅɪsᴀʙʟᴇ**")

    channel_input = args

    try:
        channel_info = await bot.get_entity(channel_input)
        channel_id = channel_info.id
        channel_title = channel_info.title
        
        # Generate invite link
        from telethon.tl.functions.messages import ExportChatInviteRequest
        invite_link = await bot(ExportChatInviteRequest(channel_id))
        channel_link = invite_link.link
        
        channel_username = f"{channel_info.username}" if hasattr(channel_info, 'username') and channel_info.username else channel_link
        
        # Get members count
        from telethon.tl.functions.channels import GetFullChannelRequest
        full_channel = await bot(GetFullChannelRequest(channel=channel_info))
        channel_members_count = full_channel.full_chat.participants_count

        # Check if bot is admin
        bot_id = (await bot.get_me()).id
        bot_is_admin = False
        
        try:
            bot_participant = await bot(GetParticipantRequest(channel=channel_id, participant=bot_id))
            if isinstance(bot_participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                bot_is_admin = True
        except UserNotParticipantError:
            bot_is_admin = False

        if not bot_is_admin:
            me = await app.get_me()
            return await event.reply(
                file="https://graph.org/file/8e1e242d4fec73ab9a8a9.jpg",
                message=("**🚫 I'ᴍ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪs ᴄʜᴀɴɴᴇʟ.**\n\n"
                         "**➲ ᴘʟᴇᴀsᴇ ᴍᴀᴋᴇ ᴍᴇ ᴀɴ ᴀᴅᴍɪɴ ᴡɪᴛʜ:**\n\n"
                         "**➥ Iɴᴠɪᴛᴇ Nᴇᴡ Mᴇᴍʙᴇʀs**\n\n"
                         "🛠️ **Tʜᴇɴ ᴜsᴇ /join <ᴄʜᴀɴɴᴇʟ ᴜsᴇʀɴᴀᴍᴇ> ᴛᴏ sᴇᴛ ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ.**"),
                buttons=[
                    [Button.url("๏ ᴀᴅᴅ ᴍᴇ ɪɴ ᴄʜᴀɴɴᴇʟ ๏", f"https://t.me/{me.username}?startchannel=s&admin=invite_users+manage_chat")]
                ]
            )

        await forcesub_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"channel_id": channel_id, "channel_username": channel_username}},
            upsert=True
        )

        set_by_user = f"@{event.sender.username}" if event.sender.username else event.sender.first_name

        await event.reply(
            file="https://graph.org/file/8e1e242d4fec73ab9a8a9.jpg",
            message=(
                f"**🎉 ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ sᴇᴛ ᴛᴏ** [{channel_title}]({channel_username}) **ғᴏʀ ᴛʜɪs ɢʀᴏᴜᴘ.**\n\n"
                f"**🆔 ᴄʜᴀɴɴᴇʟ ɪᴅ:** `{channel_id}`\n"
                f"**🖇️ ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ:** [ɢᴇᴛ ʟɪɴᴋ]({channel_link})\n"
                f"**📊 ᴍᴇᴍʙᴇʀ ᴄᴏᴜɴᴛ:** {channel_members_count}\n"
                f"**👤 sᴇᴛ ʙʏ:** {set_by_user}"
            ),
            buttons=[
                [Button.inline("๏ ᴄʟᴏsᴇ ๏", data="close_force_sub")]
            ]
        )

    except Exception as e:
        await event.reply(
            file="https://graph.org/file/8e1e242d4fec73ab9a8a9.jpg",
            message=("**🚫 ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴇᴅ!**\n\n"
                     f"**ᴇʀʀᴏʀ:** `{str(e)}`\n\n"
                     "**ᴘᴏssɪʙʟᴇ ʀᴇᴀsᴏɴs:**\n"
                     "• I'ᴍ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ\n"
                     "• Iɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ᴜsᴇʀɴᴀᴍᴇ/ID\n"
                     "• Tʜᴇ ᴄʜᴀɴɴᴇʟ ɪs ᴍᴀɴɴᴇᴍ"),
            buttons=[
                [Button.inline("๏ ᴛʀʏ ᴀɢᴀɪɴ ๏", data="close_force_sub")]
            ]
        )

# Close and cancel button callbacks
@app.on(events.CallbackQuery(pattern="close_force_sub"))
async def close_force_sub(event):
    await event.answer("ᴄʟᴏsᴇᴅ!")
    await event.delete()

@app.on(events.CallbackQuery(pattern="cancel_setjoin"))
async def cancel_setjoin(event):
    chat_id = event.chat.id
    user_id = event.sender_id
    
    if not await is_admin(chat_id, user_id):
        return await event.answer("Only admins can use this!", alert=True)
    
    config = await forcesub_collection.find_one({"chat_id": chat_id})
    enabled = config.get("enabled", False) if config else False
    
    await event.edit(
        "**📱 Force Subscription Settings**",
        buttons=[
            [Button.inline("Single Channel", data="set_single")],
            [Button.inline("Multiple Channels", data="set_multiple")],
            [Button.inline("✅ Enable" if not enabled else "❌ Disable", 
             data="fsub_on" if not enabled else "fsub_off")]
        ]
    )

# Add new command handler for /setjoin
@app.on(events.NewMessage(pattern="/setjoin"))
async def setjoin_command(event):
    if await check_fsub_handler(event):
        return
    if not event.is_group:
        return await event.reply("**⚠️ This command can only be used in groups!**")
        
    chat_id = event.chat_id
    user_id = event.sender_id
    
    if not await is_admin(chat_id, user_id):
        return await event.reply("**🚫 Only admins can use this command!**")
    
    await event.reply(
        "**📝 ʜᴏᴡ ᴛᴏ ᴜsᴇ ғᴏʀᴄᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ**\n\n"
        "**sɪɴɢʟᴇ ᴄʜᴀɴɴᴇʟ:**\n"
        "• /join @channel\n"
        "• /join -100123456789\n\n"
        "**ᴍᴜʟᴛɪᴘʟᴇ ᴄʜᴀɴɴᴇʟs (ᴍᴀx 4):**\n"
        "• /join @ch1 @ch2 @ch3\n"
        "• /join -100123456789 -100987654321\n\n"
        "**ᴅɪsᴀʙʟᴇ ғᴏʀᴄᴇsᴜʙ:**\n"
        "• /join off\n\n"
        "**ɴᴏᴛᴇ:** ᴍᴀᴋᴇ sᴜʀᴇ ɪ'ᴍ ᴀᴅᴍɪɴ ɪɴ ᴀʟʟ ᴄʜᴀɴɴᴇʟs"
    )

@app.on(events.CallbackQuery(pattern=r"set_(single|multiple)"))
async def setjoin_callback(event):
    mode = event.pattern_match.group(1)
    chat_id = event.chat.id
    user_id = event.sender_id
    
    # Check if user is admin
    if not await is_admin(chat_id, user_id):
        return await event.edit("**🚫 Only admins can use this command!**")
    
    # Initialize configuration
    config = {
        "chat_id": chat_id,
        "mode": mode,
        "channels": [],
        "enabled": False
    }
    
    await forcesub_collection.update_one(
        {"chat_id": chat_id},
        {"$set": config},
        upsert=True
    )
    
    if mode == "single":
        msg = ("**✏️ Send channel information:**\n\n"
               "**You can use:**\n"
               "• Channel Username: @channel\n"
               "• Channel ID: -100123456789\n"
               "• Channel Link: https://t.me/channel\n\n"
               "**Note:** Make sure I'm admin in the channel with invite users permission")
    else:
        msg = ("**✏️ Send up to 4 channels separated by space:**\n\n"
               "**Examples:**\n"
               "• @channel1 @channel2\n"
               "• -100123456789 -100987654321\n"
               "• https://t.me/ch1 @channel2 -100123456789\n\n"
               "**Note:** Make sure I'm admin in all channels with invite users permission")
        
    await event.edit(
        msg,
        buttons=[
            [Button.inline("« Back", data="cancel_setjoin")]
        ]
    )

# Modify join command to check setjoin first
@app.on(events.NewMessage(pattern=r"[/!\.](join|fsub|forcesub)($| .+)"))
async def set_forcesub(event):
    if not event.is_group:
        return await event.reply("**⚠️ This command can only be used in groups!**")
        
    chat_id = event.chat_id
    user_id = event.sender_id
    
    if not await is_admin(chat_id, user_id):
        return await event.reply("**🚫 Only admins can use this command!**")

    args = event.pattern_match.group(2).strip()
    
    # Handle disable command
    if args.lower() in ["off", "disable"]:
        await forcesub_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": False}}
        )
        return await event.reply("**✅ Force subscription has been disabled**")
    
    # Check if setjoin was configured
    config = await forcesub_collection.find_one({"chat_id": chat_id})
    if not config:
        return await event.reply(
            "**⚠️ Please configure force subscription first using /setjoin**",
            buttons=[
                [Button.inline("Configure Now", data="set_single")],
                [Button.inline("« Back", data="cancel_setjoin")]
            ]
        )
    
    # If no arguments provided, show current status
    if not args:
        enabled = config.get("enabled", False)
        mode = config.get("mode", "single")
        channels = config.get("channels", [])
        
        status_text = "**📱 Force Subscription Status**\n\n"
        status_text += f"**Status:** {'Enabled' if enabled else 'Disabled'}\n"
        status_text += f"**Mode:** {mode.title()}\n"
        status_text += f"**Channels:** {len(channels)}\n\n"
        
        if channels:
            status_text += "**Configured Channels:**\n"
            for i, channel in enumerate(channels, 1):
                status_text += f"{i}. {channel.get('title', 'Unknown')} [`{channel.get('id')}`]\n"
        
        return await event.reply(
            status_text,
            buttons=[
                [
                    Button.inline("✅ Enable", data="fsub_on"),
                    Button.inline("❌ Disable", data="fsub_off")
                ],
                [Button.inline("🔄 Reconfigure", data="set_single")],
                [Button.inline("« Back", data="cancel_setjoin")]
            ]
        )
    
    # Process channel arguments
    try:
        channels = args.split()
        if len(channels) > 4:
            return await event.reply("**⚠️ Maximum 4 channels allowed!**")
            
        valid_channels = []
        for channel in channels:
            try:
                channel_entity = await bot.get_entity(channel)
                channel_id = channel_entity.id
                
                # Check if bot is admin
                bot_id = (await bot.get_me()).id
                try:
                    participant = await bot(GetParticipantRequest(channel=channel_id, participant=bot_id))
                    if not isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator)):
                        return await event.reply(f"**🚫 I need to be an admin in {channel_entity.title}!**")
                except UserNotParticipantError:
                    return await event.reply(f"**🚫 I'm not even a member of {channel_entity.title}!**")
                    
                valid_channels.append({
                    "id": channel_id,
                    "title": channel_entity.title,
                    "username": channel_entity.username if hasattr(channel_entity, 'username') else None
                })
            except Exception as e:
                return await event.reply(f"**❌ Error with channel {channel}: {str(e)}**")
        
        # Update database
        await forcesub_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {
                "channels": valid_channels,
                "enabled": True,
                "mode": "multiple" if len(valid_channels) > 1 else "single"
            }},
            upsert=True
        )
        
        await event.reply(
            f"**✅ Successfully configured {len(valid_channels)} channel(s)!**\n\n"
            "**Force subscription is now enabled.**",
            buttons=[[Button.inline("« Back", data="cancel_setjoin")]]
        )
        
    except Exception as e:
        await event.reply(f"**❌ Error: {str(e)}**")

# Add callback for join enable/disable
@app.on(events.CallbackQuery(pattern=r"fsub_(on|off)"))
async def join_callback(event):
    status = event.pattern_match.group(1)
    chat_id = event.chat.id
    user_id = event.sender_id
    
    # Check if user is admin
    if not await is_admin(chat_id, user_id):
        return await event.answer("Only admins can change force subscription status!", alert=True)
    
    if status == "off":
        await forcesub_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": False}}
        )
        await event.edit(
            "**❌ Force subscription has been disabled**",
            buttons=[
                [Button.inline("✅ Enable", data="fsub_on")],
                [Button.inline("« Back", data="cancel_setjoin")]
            ]
        )
        
    else:
        config = await forcesub_collection.find_one({"chat_id": chat_id})
        if not config or not config.get("channels"):
            return await event.edit(
                "**⚠️ No channels configured. Use /setjoin first!**",
                buttons=[
                    [Button.inline("Configure Now", data="set_single")],
                    [Button.inline("« Back", data="cancel_setjoin")]
                ]
            )
            
        await forcesub_collection.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": True}}
        )
        
        channels = config.get("channels", [])
        channel_text = "\n".join([f"• {ch.get('title', 'Unknown')} [`{ch.get('id')}`]" for ch in channels])
        
        await event.edit(
            f"**✅ Force subscription has been enabled**\n\n"
            f"**Configured Channels:**\n{channel_text}",
            buttons=[
                [Button.inline("❌ Disable", data="fsub_off")],
                [Button.inline("« Back", data="cancel_setjoin")]
            ]
        )

# Modify check_forcesub to handle multiple channels
async def check_forcesub(event):
    pass
    # ... existing code ...

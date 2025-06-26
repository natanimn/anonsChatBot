from . import app, filters, Message, get_user_cache, keyboard

@app.on_message(filters.private & filters.command('premium'))
async def premium(_, message: Message, **kwargs):
    user = await get_user_cache(message.from_user.id)
    if user['is_premium']:
        subscription = user['subscription']
        await message.reply(
            f"**😊 You have already subscribed to {subscription['type']} premium feature.**\n\n"
            f"📅 __It will end on {subscription['end_date']}__"
        )
    else:
        await message.reply(
            "**💫 Premium**\n\n"
            "**🔥 Unlock premium features of the bot:**\n\n"
            "1. Filtered search.\n"
            "2. Choose your partner's: gender, age and location, and match with them.\n"
            "3. Rematch with previous partner.\n"
            "4. Delete unwanted message, while chatting from you and your partner.\n"
            "5. Daily unlimited chat.**\n\n"
            "😉 __Subscribe now__",
            reply_markup=keyboard.premium_k()
        )

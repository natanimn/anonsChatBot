from . import app, filters, Message, keyboard

@app.on_message(filters.private & filters.command('setting'))
async def setting(_, message: Message, **kwargs):
    await message.reply(
        f"**⚙️ Setting**\n\n"
        f"✔️ __From this menu, you can customize your profile: gender, age and country.__\n\n"
        f"**🔥 If you are premium user, you can also customize your preference.**\n"
        f"(__this will increase the matching time__)",
        reply_markup=keyboard.setting_k()
    )

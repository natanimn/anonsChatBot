from . import (
    app,
    filters,
    Message,
    user_exists,
    insert_user,
    create_user_cache,
    keyboard
)

@app.on_message(filters.private & filters.command('start'))
async def start(_, message: Message):
    user_id = message.from_user.id

    if not await user_exists(user_id):
        await insert_user(user_id)
        await create_user_cache(user_id)
        await message.reply(
            "**🌼 Welcome**\n\n"
            "❕ __To continue, you have to select your gender first__",
            reply_markup=keyboard.first_time_gender()
        )
    else:
        await message.reply(
        f"👋 **Hello {message.from_user.mention}**,\n\n"
        f"__Welcome to anonymous chat bot. I help you find a new "
        f"friend on telegram from all over the world. __\n\n"
        f"**Happy chatting! 😊**",
        reply_markup=keyboard.main()
    )


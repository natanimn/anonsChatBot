from pyrogram import Client as app, filters
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, Message, ForceReply
from cache.cache import get_value
from core.util import get_user, update_user
from core import check
from keyboards import keyboard
from core.state import State as _State
from pyrogram_patch.fsm.states import StateItem, State, StatesGroup
from pyrogram_patch.fsm.filter import StateFilter
from datetime import datetime, timedelta
from config import Config
from schedules.schedule import async_scheduler, unrestrict_user

class ReportState(StatesGroup):
    get_proof = StateItem()

@app.on_callback_query(filters.create(check.report))
async def report_chat(_, call: CallbackQuery):
    await call.answer()
    partner_id = call.data.split(":")[-1]
    is_premium = await get_value(call.from_user.id, 'is_premium')

    await call.edit_message_text(
        "__Chose a category of your report__",
        reply_markup=keyboard.report_categories_k(partner_id, is_premium)
    )

@app.on_callback_query(filters.create(check.c_report))
async def c_report(_, call: CallbackQuery, state: State):

    category, partner_id = call.data.split(":")[1:]

    if category == 'cancel':
        await call.edit_message_text(
            "**❌ Report cancelled**\n\n"
            "😊 __Press /chat and find new partner__",
            reply_markup=keyboard.main()
        )
    else:
        await call.edit_message_reply_markup()
        await call.message.reply(
            "❗️ __To help us understand the situation and take an action on the person, "
            "please attach an screenshoot of a message the person sent.__",
            reply_markup=ForceReply()
        )
        data = {
            'category': category,
            'partner_id': int(partner_id)
        }
        await state.set_state(ReportState.get_proof)
        await state.set_data(data)


@app.on_message(filters.create(StateFilter(ReportState.get_proof)))
async def get_report_proof(bot: app, message: Message, state: State):
    data = await state.get_data()
    partner_id = data['partner_id']
    if not message.photo:
        await message.reply("**Please attach only a photo**", reply_markup=ForceReply())
    else:
        partner = await get_user(partner_id)
        if partner.report_count + 1 >= 10:
            tomorrow = datetime.now() + timedelta(days=1)
            await update_user(
                partner_id,
                report_count=10,
                current_state=_State.RESTRICTED,
                release_date=tomorrow
            )
            try:
                await bot.send_message(
                    partner_id,
                    "**Dear user**,\n\n"
                    f"__❗️Due to rule violation, and you have been reported frequently by many users, "
                    f"you are restricted from chatting with anyone until {tomorrow}__"
                )
            finally:
                async_scheduler.add_job(
                    unrestrict_user,
                    'date',
                    run_date=tomorrow,
                    args=(partner_id,),
                    id=f'ban_user-{partner_id}'
                )

        else:
            await update_user(
                partner_id,
                report_count=partner.report_count + 1,
            )
            if partner.report_count == 5:
                try:
                    await bot.send_message(
                        partner_id,
                        "**⚠️ Warning**,\n\n"
                        f"__❗️You are frequently reported by many users. "
                        f"Please be aware that you don't violate the rules.__ "
                    )
                except RPCError:
                    pass

        await message.reply(
            "**Thankyou for your participation**\n\n"
            "__We will review the report and take an action__.",
            reply_markup=keyboard.main()
        )
        try:
            await bot.send_photo(
                Config.REPORT_CHANNEL_ID,
                message.photo.file_id,
                f"**REPORTER ID**: <code>{message.from_user.id}</code>\n"
                f"**REPORT CATEGORY**: {data['category']}\n"
                f"**REPORTED USER ID**: <code>{data['partner_id']}</code>"
            )
        finally:
            await state.finish()

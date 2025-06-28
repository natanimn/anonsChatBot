import json

from pyrogram import Client as app, filters
from pyrogram.errors import RPCError
from pyrogram.types import CallbackQuery, Message
from core import check
from core.var import PREMIUM
from keyboards import keyboard
from cache.cache import get_value, update_user_cache
from core.util import update_user, update_user_preference
from pyrogram_patch.fsm.states import State, StateItem, StatesGroup
from pyrogram_patch.fsm.filter import StateFilter
from pyrogram.types import LabeledPrice
import uuid
from .commands import premium, start, setting


class AgeState(StatesGroup):
    age = StateItem()
    age_range = StateItem()

@app.on_callback_query(filters.create(check.setting))
async def on_setting(_, call: CallbackQuery, state: State | None):
    await call.answer()
    data = call.data.split(":")[-1]
    user_id = call.from_user.id

    # await state.finish()

    if data == 'gender':
        gender = await get_value(user_id, 'gender')
        await call.edit_message_text(
            "**👤 Gender**\n\n"
            f"__Your current gender__: {gender}",
            reply_markup=keyboard.gender_k(gender)
        )
    elif data == 'age':
        age = await get_value(user_id, 'age')
        await call.edit_message_text(
            f"**Your age**: {age}\n"
            f"Enter your age",
            reply_markup=keyboard.back()
        )
        await state.set_state(AgeState.age)
        await state.set_data({'user_id': call.from_user.id})

    elif data == 'country':
        country = await get_value(user_id, 'country')
        await call.edit_message_text(
            "**🌍 Country**\n\n"
            f"__Your current country is__: {country}",
            reply_markup=keyboard.country_k(country)
        )

    elif data == 'preferences':
        is_premium = await get_value(user_id, 'is_premium')
        if not is_premium:
            try:
                await call.edit_message_text(
                    "**☝️ Premium Subscription Required**\n\n"
                    "❕__Subscribe to premium and customizes your preference:__\n\n"
                    "Age\nGender\nCountry",
                    reply_markup=keyboard.preferences_k(True)
                )
            except RPCError:
                await premium.premium(_, call.message)

        else:
            preference = await get_value(user_id, 'preference')
            await call.edit_message_text(
                "**ℹ️ Preferences**\n\n"
                f"__Gender__: {preference.get('gender', "Both")}\n"
                f"__Age range__: {preference.get('min_age', '')} - {preference.get('max_age', '')}\n"
                f"__Countries__: {', '.join(preference.get('country', []))}",
                reply_markup=keyboard.preferences_k()
        )
    else:
        try:
            await state.finish()
        finally:
            await call.edit_message_text(
                f"**⚙️ Setting**\n\n"
                f"✔️ __From this menu, you can customize your profile: gender, age and country.__\n\n"
                f"**🔥 If you are premium user, you can also customize your preference.**\n"
                f"(__this will increase the matching time__)",
                reply_markup=keyboard.setting_k()
            )

@app.on_callback_query(filters.create(check.gender))
async def on_gender(_, call: CallbackQuery):
    gender = call.data.split(":")[-1]
    if gender == 'none':
        await update_user(call.from_user.id, gender=None)
    else:
        await update_user(call.from_user.id, gender=gender)

    call.data = 'setting:gender'
    await on_setting(_, call, None)


@app.on_callback_query(filters.create(check.country))
async def on_country(_, call: CallbackQuery):
    country = call.data.split(":")[-1]
    user_id = call.from_user.id
    user_country = await get_value(user_id, 'country')
    user_region  = await get_value(user_id, 'india_region')

    if country == user_country:
        await update_user(call.from_user.id, country=None, india_region=None)
    else:
        if country != 'india':
            await update_user(call.from_user.id, country=country, india_region=None)
        else:
            await update_user(call.from_user.id, country=country)
            await call.edit_message_text(
                "**Select your indian region.\n\n"
                "__It helps you connect simply with other indian, from similar region__",
                reply_markup=keyboard.india_regions_k(user_region)
            )
            return

    call.data = 'setting:country'
    await on_setting(_, call, None)


@app.on_message(filters.text & filters.create(StateFilter(AgeState.age)))
async def on_update_age(_, message: Message, state: State):
    if not message.text.isdigit():
        await message.reply(
            "**❌ Invalid age**\n\n"
            "__Please enter valid age__",
            reply_markup=keyboard.back()
        )
    else:
        await update_user(message.from_user.id, age=int(message.text))
        await state.finish()
        await message.reply("✅ **Age updated**")
        await setting.setting(_, message)


@app.on_callback_query(filters.create(check.india_region))
async def on_indian_region(_, call: CallbackQuery):
    region = call.data.split(":")[-1]
    user_id = call.from_user.id
    user_country = await get_value(user_id, 'country')
    user_region  = await get_value(user_id, 'india_region')

    if user_country != 'india':
        await call.answer("This option is only available for Indian users", show_alert=True)
        await update_user(call.from_user.id, india_region=None)
        call.data = 'setting:country'
        await on_setting(_, call, None)

    else:
        if region == '0':
            await call.edit_message_text(
                "**Select your Indian region.\n\n"
                "__It helps you connect simply with other Indian from similar region__\n\n"
                f"**Your region:** __{user_region.title()}__",
                reply_markup=keyboard.india_regions_k(user_region)
            )

        else:
            if region == user_region:
                await update_user(call.from_user.id, india_region=None)
            else:
                await update_user(call.from_user.id, india_region=region)
            call.data = 'indian_region:0'
            await on_indian_region(_, call)


@app.on_callback_query(filters.create(check.preference))
async def on_preference(_, call: CallbackQuery, state: State | None):
    await call.answer()
    data = call.data.split(":")[-1]
    user_id = call.from_user.id
    is_premium = await get_value(user_id, 'is_premium')

    if not is_premium:
        call.data = 'setting:preferences'
        await on_setting(_, call, state)
        return

    preference = await get_value(user_id, 'preference')
    if data == 'gender':
        gender = preference.get('gender', 'Both')
        await call.edit_message_text(
            "**👤 Gender**\n\n"
            f"__Preference__: {gender}",
            reply_markup=keyboard.preference_gender_k(gender)
        )
    elif data == 'age':
        min_age = preference.get('min_age')
        max_age = preference.get('max_age')
        await call.edit_message_text(
            f"**Age range**: {min_age} - {max_age}\n\n"
            f"Enter your preference age range as: min age, max age",
            reply_markup=keyboard.back_p()
        )
        await state.set_state(AgeState.age_range)

    elif data == 'countries':
        countries = preference.get('country', [])
        await call.edit_message_text(
            "**🌍 Country**\n\n"
            f"__Preferences: {', '.join(countries)}",
            reply_markup=keyboard.preference_country_k(countries)
        )

    elif data == 'indian_region':
        regions = preference.get('indian_region', [])
        await call.edit_message_text(
            "**Indian region.\n\n"
            f"**Preference:** {', '.join(regions)}__",
            reply_markup=keyboard.india_regions_preference_k(regions)
        )

    else:
        try:
            await state.finish()
        finally:
            call.data = 'setting:preferences'
            await on_setting(_, call, state)


@app.on_callback_query(filters.create(check.gender_preference))
async def on_gender_preference(_, call: CallbackQuery):
    gender = call.data.split(":")[-1]
    user_id = call.from_user.id
    is_premium = await get_value(user_id, 'is_premium')

    if not is_premium:
        call.data = 'setting:preferences'
        await on_setting(_, call, None)
        return

    if gender == 'none':
        await update_user_preference(call.from_user.id, gender=None)
    else:
        await update_user_preference(call.from_user.id, gender=gender)

    call.data = 'preference:gender'
    await on_preference(_, call, None)


@app.on_callback_query(filters.create(check.country_preference))
async def on_country_preference(_, call: CallbackQuery):
    country = call.data.split(":")[-1]
    user_id = call.from_user.id
    is_premium = await get_value(user_id, 'is_premium')

    if not is_premium:
        call.data = 'setting:preferences'
        await on_setting(_, call, None)
        return

    preference = await get_value(user_id, 'preference')
    countries: list = preference.get('country', [])

    if country in countries:
        countries.remove(country)
    else:
        countries.append(country)

    await update_user_preference(call.from_user.id, country=countries)
    call.data = 'preferences:countries'
    await on_preference(_, call, None)


@app.on_message(filters.text & filters.create(StateFilter(AgeState.age_range)))
async def on_age_range(_, message: Message, state: State):
    ages = message.text.split(',')

    user_id = message.from_user.id
    is_premium = await get_value(user_id, 'is_premium')

    if not is_premium:
        await message.reply('.', reply_markup=keyboard.main())
        await state.finish()
        await premium.premium(_, message)
        return
    try:
        assert len(ages)== 2
        for age in ages:
            assert age.strip().isdigit()
        assert int(ages[0]) < int(ages[1])

    except AssertionError:
        await message.reply(
            "**❌ Invalid age range**\n\n"
            "__Please enter valid age as: min age, max age__",
            reply_markup=keyboard.back_p()
        )

    else:
        await update_user_preference(message.from_user.id, min_age=int(ages[0]), max_age=int(ages[1]))
        await state.finish()
        await message.reply("✅ **Age updated**")
        preference = await get_value(message.from_user.id, 'preference')
        await message.reply(
            "**ℹ️ Preferences**\n\n"
            f"__Gender__: {preference.get('gender', '')}\n"
            f"__Age range__: {preference.get('min_age', '')} - {preference.get('max_age', '')}\n"
            f"__Countries__: {', '.join(preference.get('country', []))}",
            reply_markup=keyboard.preferences_k()
        )


@app.on_callback_query(filters.create(check.india_region_preference))
async def on_i_region_preference(_, call: CallbackQuery):
    region = call.data.split(":")[-1]
    user_id = call.from_user.id
    is_premium = await get_value(user_id, 'is_premium')
    country    = await get_value(user_id, 'country')

    if not is_premium:
        call.data = 'setting:preferences'
        await on_setting(_, call, None)
        return

    if country != 'india':
        await call.answer("This option is only available for Indian users", show_alert=True)
        call.data = 'setting:preferences'
        await on_setting(_, call, None)


    preference = await get_value(user_id, 'preference')
    regions: list = preference.get('indian_region', [])

    if region in regions:
        regions.remove(regions)
    else:
        regions.append(region)

    await update_user_preference(call.from_user.id, indian_region=regions)
    call.data = 'preferences:indian_region'
    await on_preference(_, call, None)


@app.on_callback_query(filters.create(check.subscribe_premium))
async def subscribe_premium(bot: app, call: CallbackQuery):
    data = call.data.split(':')[-1]
    user_id = call.from_user.id
    price = PREMIUM[data]

    is_premium = await get_value(user_id, 'is_premium')
    if is_premium:
        await call.answer(
            "You have already subscribed to premium. "
            "You cannot subscribe twice.",
            show_alert=True
        )
        await call.edit_message_reply_markup()
        return


    hash_ = str(uuid.uuid4())
    # await update_user_cache(user_id, premium=json.dumps({'hash': hash_, 'price': price, 'id': data}))
    labeled_price = LabeledPrice(f"{price}", price)

    await bot.send_invoice(
        user_id,
        "Subscribe to Premium",
        "Subscribe to premium, and unlock premium features",
        data,
        "XTR",
        prices=[labeled_price]
    )



@app.on_callback_query(filters.create(check.first))
async def first_gender(_, call: CallbackQuery):

    await call.answer()
    user_id = call.from_user.id
    gender  = call.data.split(":")[-1]
    current_gender = await get_value(user_id, 'gender')

    if gender == 'next':
        await call.edit_message_reply_markup()
        call.message.from_user.id = call.from_user.id
        await start(_, call.message)

    else:
        if gender == current_gender:
            gender = None
        await call.edit_message_text(
            "**🌼 Welcome**\n\n"
            "❕ __To continue, you have to select your gender first__",
            reply_markup=keyboard.first_time_gender(gender)
        )
        await update_user(user_id, gender=gender)

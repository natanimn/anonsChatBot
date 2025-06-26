from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from core.var import COUNTRIES, INDIA_REGIONS, REPORTS

keyboards = ['👥 Chat', '⚙️ Setting', '💫 Premium', '❓Help', 'ℹ️ About', '🔄 Re Chat']

def main():
    return ReplyKeyboardMarkup([
        [keyboards[0], keyboards[5]],
        [keyboards[1], keyboards[2]],
        [keyboards[3], keyboards[4]]
    ], resize_keyboard=True)

def exit_k():
    return ReplyKeyboardMarkup([["🔙 Exit"]], resize_keyboard=True)

def premium_k():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐️ 100 / $1.99 — Weekly", 'subscribe_premium:1')],
        [InlineKeyboardButton("⭐️ 250 / $3.99 — Monthly", 'subscribe_premium:2')],
        [InlineKeyboardButton("⭐️ 100 / $19.99 — Annual", 'subscribe_premium:3')]
    ])

def setting_k():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Gender", 'setting:gender')
        ],
        [
            InlineKeyboardButton("🔢 Age", 'setting:age'),
            InlineKeyboardButton("🌍 Country", 'setting:country')
        ],
        [
            InlineKeyboardButton("🔐 Preferences", 'setting:preferences')
        ]
    ])

def preferences_k(locked=False):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Gender" if not locked else "🔐 Gender", 'preferences:gender'),
            InlineKeyboardButton("🔢 Age Range" if not locked else "🔐 Age Range", 'preferences:age')
        ],
        [
            InlineKeyboardButton("🌍 Countries" if not locked else "🔐 Countries", 'preferences:countries'),
        ],
        [InlineKeyboardButton("🔙 Back", 'setting:back')]
    ])

def first_time_gender(current=None):
    male = "Male ☑️" if current == 'male' else "Male"
    female = "Female ☑️" if current == 'female' else "Female"
    btn = []
    if current:
        btn.append(InlineKeyboardButton("🔜 Next", 'first:next'))

    return InlineKeyboardMarkup([[
            InlineKeyboardButton(male, 'first:male'),
            InlineKeyboardButton(female, 'first:female'),
        ],
        btn
    ])


def gender_k(current_gender):

    male = "Male ☑️" if current_gender == 'male' else "Male"
    female = "Female ☑️" if current_gender == 'female' else "Female"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(male, 'gender:male'),
            InlineKeyboardButton(female, 'gender:female'),
        ],
        [InlineKeyboardButton("🔙 Back", 'setting:back')]
    ])

def preference_gender_k(current_preference):
    male = "Male ☑️" if current_preference == 'male' else "Male"
    female = "Female ☑️" if current_preference == 'female' else "Female"
    none = "Both ☑️" if current_preference is None or current_preference == "Both" else "Both"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(male, 'pr_gender:male'),
            InlineKeyboardButton(female, 'pr_gender:female'),
        ],
        [
            InlineKeyboardButton(none, 'pr_gender:none')
        ],
        [InlineKeyboardButton("🔙 Back", 'setting:preferences')]
    ])

def country_k(current_country):
    buttons = []
    for i in range(0, len(COUNTRIES), 3):
        buttons.append([
            InlineKeyboardButton(
                f"☑️ {c}" if current_country == COUNTRIES[c] else c,
                f"country:{COUNTRIES[c]}"
            )
            for c in list(COUNTRIES.keys())[i: i+3]
        ])

    if current_country == 'india':
        buttons.append([InlineKeyboardButton("India Region", 'india_region:0')])

    buttons.append([InlineKeyboardButton("🔙 Back", 'setting:back')])
    return InlineKeyboardMarkup(buttons)

def preference_country_k(selected_countries):
    buttons = []
    for i in range(0, len(COUNTRIES), 2):
        buttons.append([
            InlineKeyboardButton(
                f"☑️ {c}" if COUNTRIES[c] in selected_countries else c,
                f"pr_country:{COUNTRIES[c]}"
            )
            for c in list(COUNTRIES.keys())[i: i+2]
        ])
    if 'india' in selected_countries:
        buttons.append([InlineKeyboardButton("India Region", 'pr_india_region:0')])
    buttons.append([InlineKeyboardButton("🔙 Back", 'setting:preferences')])
    return InlineKeyboardMarkup(buttons)

def back():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Back", 'setting:back')
    ]])


def back_p():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Back", 'preferences:back')
    ]])

def india_regions_k(selected_region):
    buttons = []
    for i in range(0, len(INDIA_REGIONS), 2):
        buttons.append([
            InlineKeyboardButton(
                f"☑️ {c}" if INDIA_REGIONS[c] == selected_region else c,
                f"india_region:{INDIA_REGIONS[c]}"
            )
            for c in list(INDIA_REGIONS.keys())[i: i + 2]
        ])
    buttons.append([InlineKeyboardButton("🔙 Back", 'setting:country')])
    return InlineKeyboardMarkup(buttons)

def india_regions_preference_k(selected_region):
    buttons = []
    for i in range(0, len(INDIA_REGIONS), 3):
        buttons.append([
            InlineKeyboardButton(
                f"☑️ {c}" if INDIA_REGIONS[c] in selected_region else c,
                f"pr_india_region:{INDIA_REGIONS[c]}"
            )
            for c in list(INDIA_REGIONS.keys())[i: i + 3]
        ])
    buttons.append([InlineKeyboardButton("🔙 Back", 'preferences:country')])
    return InlineKeyboardMarkup(buttons)

def report_k(partner_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ Report", f'report_chat:{partner_id}')]
    ])


def report_categories_k(partner_id: int | str, user_is_premium: bool):

    if user_is_premium:
        REPORTS["👤 Fake gender"] =  'fake gender'

    return InlineKeyboardMarkup([
            *[
                [InlineKeyboardButton(k, f'c_report:{v}:{partner_id}')]
            for k, v in REPORTS.items()
            ],
        [
            InlineKeyboardButton("❌ Cancel Report", f'c_report:cancel:{partner_id}')
        ]

    ])


def support():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⁉️ Support", url='t.me/aioadminsbot')]
    ])

def help_k():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⁉️ Support", url='https://t.me/aioadminsbot')],
        [InlineKeyboardButton("📢 Update channel", url='https://t.me/AutoAcceptor')]
    ])

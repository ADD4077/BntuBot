from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Расписание", callback_data="schedule")
    builder.button(text="📜 Литература", switch_inline_query_current_chat="")
    builder.button(text="🗺️ Карта", callback_data="map")
    builder.button(text="🕵🏻‍♂️ Анонимный чат", callback_data="anonymous_chat")
    builder.button(text="📎 Наш Канал", url="https://t.me/BNTUnity")
    builder.button(text="🌐 Сайт БНТУ", url="https://bntu.by")
    builder.button(text="🛠️ Поддержка", callback_data="help")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def back_to_main():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    return builder.as_markup()


def auth_error():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔐 Вручную", callback_data="support_auth")
    return builder.as_markup()


def support_auth(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔐 Авторизовать", callback_data=f"accept_auth {user_id}")
    builder.button(text="Отклонить", callback_data="decline_auth")
    builder.adjust(1, 1)
    return builder.as_markup()


def anonymous_chat_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔎 Начать поиск", callback_data="search_anonymous_chat")
    builder.button(text="Правила чата", url="https://telegra.ph/Pravila-Anonimnogo-CHata-09-14")
    builder.adjust(1, 1)
    return builder.as_markup()


def report_menu(reported_user_id: int, sender_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Забанить нарушителя", callback_data=f"ban_user {reported_user_id}")
    builder.button(text="Забанить отправителя", callback_data=f"ban_user {sender_id}")
    return builder.as_markup()


def admin_panel_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Поиск пользователя", callback_data="search_user")
    builder.button(text="Поиск группы", callback_data="search_group")
    builder.button(text="Расписание", callback_data="admin_schedule")
    builder.button(text="Литература", callback_data="admin_literature")
    builder.adjust(2, 2)
    return builder.as_markup()


def map_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Убрать", callback_data="delete")
    return builder.as_markup()


def passes_menu(passes: dict):
    builder = InlineKeyboardBuilder()
    for subj in passes.keys():
        builder.button(text=subj, callback_data=f"get_passes {subj}")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1)
    return builder.as_markup()


def pass_detail_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="passes")
    return builder.as_markup()


def schedule_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Сегодня", callback_data="send_schedule together")
    builder.button(text="Завтра", callback_data="send_schedule tomorrow")
    builder.button(text="Эта неделя", callback_data="send_schedule week")
    builder.button(text="След. неделя", callback_data="send_schedule next_week")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def back_to_schedule():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="schedule")
    return builder.as_markup()


def help_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Политика конфиденциальности", url="https://telegra.ph/Politika-konfidencialnosti-09-08-51")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1, 1)
    return builder.as_markup()

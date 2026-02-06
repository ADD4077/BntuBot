from aiogram.utils.keyboard import InlineKeyboardBuilder
import json

from bs4 import builder


def main_menu_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎓 Студсовет", callback_data="studsovet")
    builder.button(text="📅 Расписание", callback_data="schedule")
    builder.button(text="📜 Литература", switch_inline_query_current_chat="")
    builder.button(text="🗺 Карта", callback_data="map")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.adjust(1, 2, 2)
    return builder.as_markup()


def studsovet_buttons(is_owner):
    builder = InlineKeyboardBuilder()
    builder.button(text="💼 Советы", callback_data="studsovet_staff_menu")
    builder.button(text="🍻 Мероприятия БНТУ", callback_data="events bntu 1")
    builder.button(text="🍻 Мероприятия", callback_data="events studsovet 1")
    builder.button(text="💡 Идеи и жалобы", callback_data="studsovet_support")
    if is_owner:
        builder.button(text="Добавить мероприятие", callback_data="add_event")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    if is_owner:
        builder.adjust(1, 1, 1, 1, 1, 1)
        return builder.as_markup()
    builder.adjust(1, 1, 1, 1, 1)
    return builder.as_markup()


def events_buttons(event_type, page, count, is_owner, event_id):
    builder = InlineKeyboardBuilder()
    page = int(page)
    builder.button(text="⏪", callback_data=f"events {event_type} 1")
    builder.button(
        text="◀️", callback_data=f"events {event_type} {page - 1 if page != 1 else 1}"
    )
    builder.button(text=f"{page}/{count}", callback_data=f"page {page}")
    builder.button(
        text="▶️",
        callback_data=f"events {event_type} {page + 1 if page != count else page}",
    )
    builder.button(text="⏩", callback_data=f"events {event_type} {count}")
    builder.button(text="⬅️ Назад", callback_data="studsovet")
    if is_owner:
        builder.button(
            text="Удалить мероприятие", callback_data=f"delete_event {event_id}"
        )
        builder.button(
            text="Редактировать мероприятие", callback_data=f"edit_event {event_id}"
        )
        builder.adjust(5, 1, 1, 1)
        return builder.as_markup()
    builder.adjust(5, 1)
    return builder.as_markup()


def edit_event_choose(event_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"edit_event {event_id} name")
    builder.button(text="Описание", callback_data=f"edit_event {event_id} description")
    builder.button(text="Дата", callback_data=f"edit_event {event_id} date")
    builder.button(text="Контакты", callback_data=f"edit_event {event_id} contacts")
    builder.button(text="Участники", callback_data=f"edit_event {event_id} members")
    builder.button(text="Изображение", callback_data=f"edit_event {event_id} image")
    builder.adjust(1, 1, 1, 1, 1, 1)
    return builder.as_markup()


def choose_support_type():
    builder = InlineKeyboardBuilder()
    builder.button(text="Анонимно", callback_data="studsovet_support anonymous")
    builder.button(text="Не анонимно", callback_data="studsovet_support not_anonymous")
    builder.button(text="⬅️ Назад", callback_data="studsovet return")
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def studsovet_staff_menu_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="АТФ", callback_data="student_coucil_staff АТФ")
    builder.button(text="ФГДИЭ", callback_data="student_coucil_staff ФГДИЭ")
    builder.button(text="МСФ", callback_data="student_coucil_staff МСФ")
    builder.button(text="МТФ", callback_data="student_coucil_staff МТФ")
    builder.button(text="ФММП", callback_data="student_coucil_staff ФММП")
    builder.button(text="ЭФ", callback_data="student_coucil_staff ЭФ")
    builder.button(text="ФИТР", callback_data="student_coucil_staff ФИТР")
    builder.button(text="ФТУГ", callback_data="student_coucil_staff ФТУГ")
    builder.button(text="ИПФ", callback_data="student_coucil_staff ИПФ")
    builder.button(text="ФЭС", callback_data="student_coucil_staff ФЭС")
    builder.button(text="АФ", callback_data="student_coucil_staff АФ")
    builder.button(text="СФ", callback_data="student_coucil_staff СФ")
    builder.button(text="ПСФ", callback_data="student_coucil_staff ПСФ")
    builder.button(text="ФТК", callback_data="student_coucil_staff ФТК")
    builder.button(text="СТФ", callback_data="student_coucil_staff СТФ")
    builder.button(text="ФМС", callback_data="student_coucil_staff ФМС")
    builder.button(text="⬅️ Назад", callback_data="studsovet return")
    builder.adjust(4, 4, 4, 4, 1)
    return builder.as_markup()


def student_coucil_staff_create(faculty):
    with open(
        f"student_councils/student_council_chairmans.json", "r", encoding="utf8"
    ) as jsonfile:
        concil = json.load(jsonfile)[faculty]
    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"📖 Студсовет {faculty}",
        callback_data=f"faculty_student_council {faculty}",
    )
    if "hostels" in concil.keys():
        for hostel in concil["hostels"].keys():
            builder.button(
                text=f"🏠 Студсовет общежития {hostel}",
                callback_data=f"hostel_student_council {faculty} {hostel}",
            )
    builder.button(text="⬅️ Назад", callback_data="studsovet_staff_menu")
    builder.adjust(1, 1)
    return builder.as_markup()


def faculty_student_council_return(faculty):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ Назад", callback_data=f"student_coucil_staff {faculty} return"
    )
    builder.adjust(1)
    return builder.as_markup()


def studsovet_support_choice_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📚 Учебный процесс", callback_data="stud_support Учебный процесс"
    )
    builder.button(
        text="👨‍🏫 Преподаватели", callback_data="stud_support Преподаватели"
    )
    builder.button(text="🏠 Общежитие", callback_data="stud_support Общежитие")
    builder.button(text="📝 Другое...", callback_data="stud_support Другое")
    builder.button(text="⬅️ Назад", callback_data="studsovet return")
    builder.adjust(1, 1, 1, 1, 1)
    return builder.as_markup()


def profile_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏰ Рассылка", callback_data="scheduled_message")
    builder.button(text="🔗 Реферальная система", callback_data="referal_system")    
    builder.button(text="🛠️ Поддержка", callback_data="help")
    builder.button(text="📎 Наш Канал", url="https://t.me/BNTUnity")
    builder.button(text="🌐 Сайт БНТУ", url="https://bntu.by")
    builder.button(text="⬅️ Назад", callback_data="main_menu")
    builder.adjust(1, 1, 1, 2, 1)
    return builder.as_markup()


def select_time():
    builder = InlineKeyboardBuilder()
    builder.button(text="⏰ 6:00", callback_data="select_time 6")
    builder.button(text="⏰ 12:00", callback_data="select_time 12")
    builder.button(text="⏰ 18:00", callback_data="select_time 18")
    builder.button(text="❌ Отключить", callback_data="select_time -1")
    builder.button(text="⬅️ Назад", callback_data="profile")
    builder.adjust(3, 1)
    return builder.as_markup()


def back_to_profile():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="profile")
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
    builder.button(
        text="Правила чата", url="https://telegra.ph/Pravila-Anonimnogo-CHata-09-14"
    )
    builder.adjust(1, 1)
    return builder.as_markup()


def report_menu(reported_user_id: int, sender_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Забанить нарушителя", callback_data=f"ban_user {reported_user_id}"
    )
    builder.button(text="Забанить отправителя", callback_data=f"ban_user {sender_id}")
    return builder.as_markup()


def admin_panel_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="Поиск", callback_data="admin_search")
    builder.button(text="Расписание", callback_data="admin_schedule")
    builder.button(text="Литература", callback_data="admin_literature")
    builder.adjust(1, 1, 1, 1, 2)
    return builder.as_markup()

def admin_panel_menu_search():
    builder = InlineKeyboardBuilder()
    builder.button(text="Поиск пользователя", callback_data="search_user")
    builder.button(text="Поиск группы", callback_data="search_group")
    builder.button(text="Поиск факультета", callback_data="search_faculty")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.adjust(1, 1, 1, 1, 2)
    return builder.as_markup()

def choose_event_type(is_from_callback=None):
    builder = InlineKeyboardBuilder()
    builder.button(text="Мероприятие БНТУ", callback_data="add_event bntu")
    builder.button(text="Мероприятие студсовета", callback_data="add_event studsovet")
    if is_from_callback:
        builder.button(text="⬅️ Назад", callback_data="studsovet return")
        builder.adjust(1, 1, 1)
        return builder.as_markup()
    builder.adjust(1, 1)
    return builder.as_markup()


def search_user_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="Telegram ID", callback_data="search_by_user_id")
    builder.button(text="Cтуд. билета", callback_data="search_by_group_number")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.adjust(2, 1)
    return builder.as_markup()


def control_user_buttons(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Сообщение", callback_data=f"send_message_for_user {user_id}")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.adjust(1, 1)
    return builder.as_markup()


def control_group_buttons(group_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Рассылка", callback_data=f"send_message_for_group {group_id}")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.adjust(1, 1)
    return builder.as_markup()


def search_faculty_buttons():
    builder = InlineKeyboardBuilder()
    builder.button(text="По аббревиатуре", callback_data="search_by_faculty_abbr")
    builder.button(text="По номеру", callback_data="search_by_faculty_number")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.adjust(2, 1)
    return builder.as_markup()


def literature_and_schedule_admin_buttons(data_to_parse: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="Запарсить", callback_data=f"parse {data_to_parse}")
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.adjust(1, 1)
    return builder.as_markup()


def back_to_admin_panel():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="back_to_admin_panel")
    builder.adjust(1)
    return builder.as_markup()


def map_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="main_menu")
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


def schedule_menu_other(week):
    builder = InlineKeyboardBuilder()
    builder.button(text="Пн", callback_data=f" Понедельник {week}")
    builder.button(text="Вт", callback_data=f"send_schedule_week Вторник {week}")
    builder.button(text="Ср", callback_data=f"send_schedule_week Среда {week}")
    builder.button(text="Чт", callback_data=f"send_schedule_week Четверг {week}")
    builder.button(text="Пт", callback_data=f"send_schedule_week Пятница {week}")
    builder.button(text="Сб", callback_data=f"send_schedule_week Суббота {week}")
    builder.button(text="⬅️ Назад", callback_data="return_schedule")
    builder.adjust(3, 3, 1)
    return builder.as_markup()


def back_to_schedule():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="schedule")
    return builder.as_markup()


def help_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📪 Написать в поддержку", callback_data="message_support")
    builder.button(
        text="📝 Политика конфиденциальности",
        url="https://telegra.ph/Politika-konfidencialnosti-09-08-51",
    )
    builder.button(text="⬅️ Назад", callback_data="profile")
    builder.adjust(1, 1)
    return builder.as_markup()


def support_answer_buttons(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="Ответить", callback_data=f"answer_support {user_id}")
    builder.adjust(1)
    return builder.as_markup()

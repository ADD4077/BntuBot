from aiogram import Router, F
from aiogram.types import (
    InlineQuery,
    ChosenInlineResult,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from util.literature_searching import search_literature
from aiogram.utils.markdown import hlink

dp = Router()


@dp.inline_query()
async def inline_handler(inline_query: InlineQuery):
    query = inline_query.query or ""
    books = search_literature(literature, query)
    results = []
    for id, book in enumerate(books):
        link = hlink("⬇️ Скачать", book["download"]["download_link"])
        description = book["publishing_date"]
        message_text = f"{book['publishing_date']} | {book['title']}\n\n{book['description']}\n\n{link}"
        if book["authors"]:
            with_authors = " и др." if len(book["authors"]) != 1 else ""
            description += f" | {book['authors'][0]}{with_authors}"
            message_text = (
                f"<b>{book['publishing_date']} | {book['title']}</b>\n\n"
                f"<b>ℹ️ Описание:</b>\n{book['description']}\n\n<b>©️ Авторы:</b>\n{book['authors'][0]}{with_authors}\n\n{link}"
            )
        results.append(
            InlineQueryResultArticle(
                id=str(id),
                title=book["title"],
                input_message_content=InputTextMessageContent(
                    message_text=message_text, parse_mode="HTML"
                ),
                description=description,
                thumbnail_url=book["image_url"],
            )
        )
    await bot.answer_inline_query(inline_query.id, results)


@dp.chosen_inline_result()
async def chosen_inline_handler(result: ChosenInlineResult):
    print(result)

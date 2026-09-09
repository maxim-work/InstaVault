from aiogram.fsm.state import State, StatesGroup


class SearchState(StatesGroup):
    waiting_for_query = State()
    viewing_results = State()


class NewsletterState(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()

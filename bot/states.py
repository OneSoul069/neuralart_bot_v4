"""FSM states."""
from aiogram.fsm.state import State, StatesGroup

class AccountAuthStates(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_2fa = State()

class ImageGenStates(StatesGroup):
    waiting_prompt = State()

class PsychologistStates(StatesGroup):
    in_session = State()

class AssessmentStates(StatesGroup):
    answering = State()
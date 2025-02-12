from typing import List
from ..base.base_repository import BaseRepository
from models import GameStatus
from sqlalchemy.ext.asyncio import AsyncSession
from .exceptions.exceptions import UserNotFoundException, UserNotExistsException, UserExistsException
from sqlalchemy import select, delete, text

class GameRepository(BaseRepository[GameStatus]):
    model: GameStatus = GameStatus
    exception: UserNotFoundException = UserNotFoundException()

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=self.model, exception=self.exception)

    async def get_all_status(self):
        query = select(self.model)
        stmt = await self.session.execute(query)
        status = stmt.scalars().all()

        return status
    
    async def get_sections(self) -> list[GameStatus]:
        query = select(self.model)
        stmt = await self.session.execute(query)
        res = stmt.scalars().all()

        sections_list = (res.sections).split('.')

        if not sections_list:
            raise "Fail"
        
        return sections_list
    
    async def start_game(self, current_section_index: int, game_started: bool, game_over: bool):
        query = select(self.model)
        stmt = await self.session.execute(query)
        status = stmt.scalars().all()

        status.current_section_index = current_section_index
        status.game_started = game_started
        status.game_over = game_over

        self.session.commit()
        self.session.refresh(status)

        return {"message": "Ok"}

    async def stop_game(self, game_started: bool, game_over: bool):
        query = select(self.model)
        stmt = await self.session.execute(query)
        status = stmt.scalars().all()

        status.game_started = game_started
        status.game_over = game_over

        self.session.commit()
        self.session.refresh(status)

    async def switch_display_mode(self, display_mode: str):
        query = select(self.model)
        stmt = await self.session.execute(query)
        status = stmt.scalars().all()

        status.spectator_display_mode = display_mode

        self.session.commit()
        self.session.refresh(status)

    async def update_section_index(self, section_index: int):
        query = select(self.model)
        stmt = await self.session.execute(query)
        status = stmt.scalars().all()

        status.current_section_index = section_index

        self.session.commit()
        self.session.refresh(status)

    async def update_game_over(self, game_over: bool):
        query = select(self.model)
        stmt = await self.session.execute(query)
        status = stmt.scalars().all()

        status.game_over = game_over

        self.session.commit()
        self.session.refresh(status)

    async def update_current_question(self, current_question: str, answer_for_current_question: str, current_question_image: str, current_answer_image: str):
        query = select(self.model)
        stmt = await self.session.execute(query)
        status = stmt.scalars().all()

        status.current_question = current_question
        status.answer_for_current_question = answer_for_current_question
        status.current_question_image = current_question_image
        status.current_answer_image = current_answer_image

        self.session.commit()
        self.session.refresh(status)
        
    
    
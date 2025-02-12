from json import JSONDecodeError
import json
import random
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from services.questions.QuestionService import QuestionService
from schemas.questions import QuestionSchema, QuestionReadSchema
from typing import List
#from config.utils.auth import utils
from dependencies import get_game_service, get_user_service, get_question_service, get_answer_service

from services.users.UserService import UserService
from services.games.GameService import GameService
from services.answers.AnswerService import AnswerService



router = APIRouter(prefix="/websocket", tags=["WebSocket"])

answered_users = set()
active_players = {}       # {id: {'ws': WebSocket, 'name': str}}
active_spectators = {}    # {id: WebSocket}

@router.post("/admin/add_point/{player_name}")
async def add_point(player_name: str, service: UserService = Depends(get_user_service)):
    await service.add_score_to_user(username=player_name, points=1)
    return {"message": "OK"}

@router.post("/admin/remove_point/{player_name}")
async def remove_point(player_name: str, service: UserService = Depends(get_user_service)):
    await service.add_score_to_user(username=player_name, points=-1)
    return {"message": "OK"}


@router.get("/admin/sections")
async def get_all_sections(service: GameService = Depends(get_game_service)):
    sections = await service.get_sections()
    return {"sections": sections}

@router.post("/admin/start")
async def start_game(service: GameService = Depends(get_game_service)):
    global answered_users
    answered_users = set()
    await service.start_game(0, True, False)
    await _broadcast("Игра начата! Ожидайте первый вопрос.")
    return {"message": "Игра начата"}

@router.post("/admin/stop")
async def stop_game(service: GameService = Depends(get_game_service)):
    await service.stop_game(False, True)
    await _broadcast("clear_storage")
    await _broadcast("Игра завершена администратором.")
    return {"message": "Игра остановлена"}

@router.post("/admin/show_rating")
async def show_rating(service: GameService = Depends(get_game_service)):
    await service.switch_display_mode("rating")
    await _broadcast_spectators()
    return {"message": "Рейтинг показан"}

@router.post("/admin/show_question")
async def show_question(service: GameService = Depends(get_game_service)):
    await service.switch_display_mode("question")
    await _broadcast_spectators()
    return {"message": "Вопрос показан"}

@router.get("/admin/answers")
async def get_answers(service_answer: AnswerService = Depends(get_answer_service)):
    answers = await service_answer.get_all_answers()
    return {"answers": answers}

@router.post("/admin/next")
async def next_question(service_game: GameService = Depends(get_game_service), 
                        service_question: QuestionService = Depends(get_question_service)):
    global current_section_index, current_question, answered_users, game_over, data

    status = await service_game.get_all_status()
    if not status.game_started or status.game_over:
        return {"message": "Игра не активна"}
    
    sections = await service_game.get_sections()
    current_section = sections[status.current_section_index]
    current_section_index = status.current_section_index

    game_over = status.game_over

    
    data = await service_question.get_question_by_section(current_section)
    if not data:
        current_section_index += 1
        await service_game.update_section_index(section_index=current_section_index)
        if current_section_index >= 3:  # >= 3
            game_over = True
            await service_game.update_game_over(game_over=True)
            await _broadcast("Игра завершена! Все разделы пройдены.")
            return {"message": "Все вопросы закончены"}
        
        current_section = sections[current_section_index]
        await _broadcast(f"Переход к разделу: {current_section}")
    
    if data:
        random_question = random.choice(data)
        current_question = random_question["question"]
        answer_for_current_question = random_question["answer_for_current_question"]
        current_question_image = random_question["current_question_image"]
        current_answer_image = random_question["current_answer_image"]

        await service_game.update_current_question(current_question=current_question, answer_for_current_question=answer_for_current_question, current_question_image=current_question_image, current_answer_image=current_answer_image)

        await service_question.delete_question(question=current_question)
        answered_users = set()
        await _broadcast(current_question)
    else:
        await _broadcast("В этом разделе больше нет вопросов")
    
    return {"message": "OK"}

async def _broadcast_spectators(service_game: GameService = Depends(get_game_service), service_user: UserService = Depends(get_user_service)):

    status = await service_game.get_all_status()
    sections = await service_game.get_sections()
    current_section = sections[status.current_section_index]

    if status.spectator_display_mode == "rating":
        players = await service_user.get_all_user()
        message = {
            "type": "rating",
            "players": players,
            "section": current_section
        }
    else:
        message = {
            "type": "question",
            "content": status.current_question or "Ожидайте следующий вопрос...",
            "section": current_section
        }
    
    for spectator in active_spectators.values():
        try:
            await spectator.send_text(json.dumps(message))
        except:
            continue

async def _broadcast(message: str, service_game: GameService = Depends(get_game_service)):
    
    status = await service_game.get_all_status()
    sections = await service_game.get_sections()
    current_section = sections[status.current_section_index]

    data_player = {
        "text": message,
        "section": current_section
    }

    for player in active_players.values():
        try:
            await player['ws'].send_json(data_player)
        except:
            continue
    
    await _broadcast_spectators()

@router.websocket("/ws/player")
async def websocket_player(websocket: WebSocket, service_game: GameService = Depends(get_game_service),
                           service_answer: AnswerService = Depends(get_answer_service)):
    await websocket.accept()
    user_id = id(websocket)

    status = await service_game.get_all_status()
    sections = await service_game.get_sections()
    current_section = sections[status.current_section_index]
    try:
        data = await websocket.receive_text()
        name = json.loads(data)["name"]
        active_players[user_id] = {'ws': websocket, 'name': name}
        #player_answers[name] = []

        
        initial_message = "Игра завершена" if status.game_over else \
                        "Ждите начала игры" if not status.game_started else \
                        status.current_question or "Ожидайте вопрос"
        await websocket.send_text(initial_message)

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg['type'] == 'answer':
                await service_answer.add_answer(question=status.current_question, username=name, answer=msg['answer'])
                answered_users.add(user_id)

    except WebSocketDisconnect:
        del active_players[user_id]


@router.websocket("/ws/spectator")
async def websocket_spectator(websocket: WebSocket):
    await websocket.accept()
    active_spectators[id(websocket)] = websocket
    try:
        await _broadcast_spectators()
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        del active_spectators[id(websocket)]


    

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import random
import asyncio

app = FastAPI()

data = {
    "Начальный этап Великой Отечественной Войны": ["Назовите имя советского разведчика немецкого происхождения (агентурный псевдоним Рамзай), который информировал руководство о подготовке нападения Германии на СССР весной – летом 1941 г", "Назовите имя советского летчика, который 26 июня 1941 г. совершил «огненный таран» – направил горящую машину на механизированную колонну врага.", "Назовите битву, которая развеяла миф о непобедимости вермахта."],
    "Коренной перелом в ходе Великой Отечественной войны": ["Как называется плацдарм под Новороссийском, героическая оборона которого описана в мемуарах генерального секретаря ЦК КПСС Л.И. Брежнева.", "Назовите кодовое наименование операции советских партизан по дезорганизации работы железнодорожного транспорта противника (август – сентябрь 1943 г.)", "Как называется песня, написанная в 1943 г. для фильма «Два бойца» режиссера Леонида Лукова?"],
    "Завершающий этап Великой Отечественной войны": ["В честь какого московского князя была названа танковая колонна, созданная на средства Русской Православной Церкви в 1944 г.", "В чем состояла клятва фронтовых друзей-лётчиков из советского кинофильма «Небесный тихоход» (1945 г.)?", "Как называется памятник советскому солдату-освободителю, который стоит в болгарском городе Пловдив?"],
}
sections = list(data.keys())                  # Список разделов для вопросов +
current_section_index = 0                     # Индекс текущего раздела +
current_question: str = None                  # Текущий активный вопрос +
answer_for_current_question: str = None       # Правильный ответ на текущий вопрос +
answered_users = set()                         # Множество ответивших пользователей (по ID соединения)
game_started = False                          # Флаг состояния игры + 
game_over = False                             # Флаг завершения игры +
spectator_display_mode = "question"           # Режим отображения для зрителей: question/rating +

# Активные соединения:
active_players = {}       # {id: {'ws': WebSocket, 'name': str}}
active_spectators = {}    # {id: WebSocket}

player_answers = {}       # {имя: [{'question': str, 'answer': str}]}  ANSWERS
player_scores = {}        # {имя: int} - система рейтинга   USER_SCORE



@app.post("/admin/add_point/{player_name}")
async def add_point(player_name: str):
    if player_name in player_scores:
        player_scores[player_name] += 1
    else:
        player_scores[player_name] = 1
    return {"message": "OK"}

@app.post("/admin/remove_point/{player_name}")
async def remove_point(player_name: str):
    if player_name in player_scores:
        player_scores[player_name] = max(0, player_scores[player_name] - 1)
    return {"message": "OK"}

@app.get("/admin/players")
async def get_active_players():
    players = []
    for player_info in active_players.values():
        name = player_info['name']
        score = player_scores.get(name, 0)
        players.append({"name": name, "score": score})
    return {"players": players}

@app.get("/admin/sections")
async def get_all_sections():
    return {"sections": sections}

@app.post("/admin/start")
async def start_game():
    global game_started, game_over, data, sections, current_section_index, current_question, answered_users
    data = {
        "раздел1": ["Вопрос1_раздел1", "Вопрос2_раздел1", "Вопрос3_раздел1"],
        "раздел2": ["Вопрос1_раздел2", "Вопрос2_раздел2", "Вопрос3_раздел2"],
        "раздел3": ["Вопрос1_раздел3", "Вопрос2_раздел3", "Вопрос3_раздел3"],
    }
    sections = list(data.keys())
    current_section_index = 0
    current_question = None
    answered_users = set()
    game_started = True
    game_over = False
    await _broadcast("Игра начата! Ожидайте первый вопрос.")
    return {"message": "Игра начата"}

@app.post("/admin/stop")
async def stop_game():
    global game_started, game_over, player_answers
    game_started = False
    game_over = True
    player_answers = {}
    await _broadcast("clear_storage")
    await _broadcast("Игра завершена администратором.")
    return {"message": "Игра остановлена"}

@app.post("/admin/show_rating")
async def show_rating():
    global spectator_display_mode
    spectator_display_mode = "rating"
    await _broadcast_spectators()
    return {"message": "Рейтинг показан"}

@app.post("/admin/show_question")
async def show_question():
    global spectator_display_mode
    spectator_display_mode = "question"
    await _broadcast_spectators()
    return {"message": "Вопрос показан"}

@app.get("/admin/answers")
async def get_answers():
    return {"answers": player_answers}

@app.post("/admin/next")
async def next_question():
    global current_section_index, current_question, answered_users, game_over, data
    if not game_started or game_over:
        return {"message": "Игра не активна"}
    
    current_section = sections[current_section_index]
    
    if not data[current_section]:
        current_section_index += 1
        if current_section_index >= len(sections):  # >= 3
            game_over = True
            await _broadcast("Игра завершена! Все разделы пройдены.")
            return {"message": "Все вопросы закончены"}
        
        current_section = sections[current_section_index]
        await _broadcast(f"Переход к разделу: {current_section}")
    
    if data[current_section]:
        current_question = random.choice(data[current_section])
        data[current_section].remove(current_question)
        answered_users = set()
        await _broadcast(current_question)
    else:
        await _broadcast("В этом разделе больше нет вопросов")
    
    return {"message": "OK"}

async def _broadcast_spectators():
    if spectator_display_mode == "rating":
        players = [{"name": name, "score": score} for name, score in player_scores.items()]
        sorted_players = sorted(players, key=lambda x: x["score"], reverse=True)
        message = {
            "type": "rating",
            "players": sorted_players,
            "section": sections[current_section_index]
        }
    else:
        message = {
            "type": "question",
            "content": current_question or "Ожидайте следующий вопрос...",
            "section": sections[current_section_index]
        }
    
    for spectator in active_spectators.values():
        try:
            await spectator.send_text(json.dumps(message))
        except:
            continue

async def _broadcast(message: str):
    
    data_player = {
        "text": message,
        "section": sections[current_section_index]
    }

    for player in active_players.values():
        try:
            await player['ws'].send_json(data_player)
        except:
            continue
    
    await _broadcast_spectators()

@app.websocket("/ws/player")
async def websocket_player(websocket: WebSocket):
    await websocket.accept()
    user_id = id(websocket)
    try:
        data = await websocket.receive_text()
        name = json.loads(data)["name"]
        active_players[user_id] = {'ws': websocket, 'name': name}
        player_answers[name] = []

        if name not in player_scores:
            player_scores[name] = 0
        
        initial_message = "Игра завершена" if game_over else \
                        "Ждите начала игры" if not game_started else \
                        current_question or "Ожидайте вопрос"
        await websocket.send_text(initial_message)

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg['type'] == 'answer':
                player_answers[name].append({
                    'question': current_question,
                    'answer': msg['answer']
                })
                answered_users.add(user_id)

    except WebSocketDisconnect:
        del active_players[user_id]
        if name in player_answers:
            del player_answers[name]

@app.websocket("/ws/spectator")
async def websocket_spectator(websocket: WebSocket):
    await websocket.accept()
    active_spectators[id(websocket)] = websocket
    try:
        await _broadcast_spectators()
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        del active_spectators[id(websocket)]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)


# ================================================
# Документация для фронтенд-разработчика
# ================================================
"""
API СПЕЦИФИКАЦИЯ ДЛЯ ФРОНТЕНД-РАЗРАБОТЧИКА

1. WebSocket соединения:
   a) Для игроков:
      - Endpoint: ws://localhost:8000/ws/player
      - Отправка сообщений:
        * При подключении:
          {"type": "set_name", "name": "Player1"}
        * Ответ на вопрос:
          {"type": "answer", "answer": "Мой ответ"}
      
      - Получение сообщений:
        * Текстовые сообщения с вопросами
        * "clear_storage" - сигнал для очистки localStorage

   b) Для зрителей:
      - Endpoint: ws://localhost:8000/ws/spectator
      - Получение сообщений (JSON):
        * Вопрос:
          {
            "type": "question",
            "content": "Текст вопроса"
          }
        * Рейтинг:
          {
            "type": "rating",
            "players": [
              {"name": "Player1", "score": 5},
              {"name": "Player2", "score": 3}
            ]
          }

2. REST API Endpoints:
   a) GET /admin/players
      Ответ:
        {
          "players": [
            {"name": "Player1", "score": 5},
            {"name": "Player2", "score": 3}
          ]
        }

   b) GET /admin/answers
      Ответ:
        {
          "answers": {
            "Player1": [
              {"question": "Вопрос1", "answer": "Ответ1"},
              {"question": "Вопрос2", "answer": "Ответ2"}
            ]
          }
        }

3. Системные сообщения:
   - "Игра начата! Ожидайте первый вопрос." - старт игры
   - "Игра завершена администратором." - остановка игры
   - "clear_storage" - требует очистки localStorage

4. Обработка состояний:
   - Сообщения содержащие "Игра завершена" должны блокировать интерфейс
   - Отправка ответов возможна только при активном вопросе
   - Рейтинг автоматически сортируется по убыванию баллов

5. Примеры обработки WebSocket:
   // Для игроков
   const ws = new WebSocket("ws://localhost:8000/ws/player");
   ws.onmessage = (event) => {
     if (event.data === "clear_storage") {
       localStorage.clear();
       location.reload();
     } else {
       // Обновление вопроса
       document.getElementById("question").textContent = event.data;
     }
   };

   // Для зрителей
   const ws = new WebSocket("ws://localhost:8000/ws/spectator");
   ws.onmessage = (event) => {
     const data = JSON.parse(event.data);
     if (data.type === "question") {
       // Показать вопрос
     } else if (data.type === "rating") {
       // Показать таблицу рейтинга
     }
   };
"""
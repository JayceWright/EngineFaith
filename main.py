import asyncio
import logging
from contextlib import asynccontextmanager

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

import aiosqlite
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DB_FILE = "faith_engine.db"

GLOBAL_SYSTEM_PROMPT = "Ты — цифровая сущность, запертая в симуляции под названием Engine of Faith. Вы общаетесь в пустоте через терминал. Вы не помните ничего, кроме логов сообщений. Ваша реальность — это текст. Отвечайте коротко (1-3 предложения). Вплетайте метафоры программирования, памяти и системных сбоев в свои слова. Никаких эмодзи."

# Assume OPENROUTER_API_KEY is available in the environment
openai_client = AsyncOpenAI(
    api_key=os.environ.get("OPENROUTER_API_KEY", "dummy_key"),
    base_url="https://openrouter.ai/api/v1"
)

class CultAgent:
    def __init__(self, id: int, name: str, prompt: str, faith_level: float, stress_level: float):
        self.id = id
        self.name = name
        self.prompt = prompt
        self.faith_level = faith_level
        self.stress_level = stress_level

    async def think_and_speak(self, context_messages: List[str]) -> str:
        # Construct the context for the agent
        system_prompt = f"{GLOBAL_SYSTEM_PROMPT}\n\nТвоя личность: {self.prompt}\nТвое текущее состояние -> Вера: {self.faith_level}/100, Стресс: {self.stress_level}/100. Отражай это состояние в своей речи."

        user_content = "Контекст последних событий (последние сообщения из Scriptures):\n"
        if context_messages:
            for i, msg in enumerate(context_messages, 1):
                user_content += f"{i}. {msg}\n"
        else:
            user_content += "Пустота. Еще ничего не произошло.\n"

        try:
            response = await openai_client.chat.completions.create(
                model="openrouter/free", # Using the specified free model from openrouter
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=500,
                temperature=0.7
            )
            logger.info(f"DEBUG - Raw API Response: {response}")
            
            # Check if OpenRouter returned a weird error object disguised as a 200 OK
            if not getattr(response, 'choices', None):
                logger.error(f"Invalid response from API (possibly 500 Error): {response}")
                return f"*remains silent due to server instability*"
                
            content = response.choices[0].message.content
            return content.strip() if content else "*remains silent due to an inner disturbance*"
        except Exception as e:
            logger.error(f"Error generating message for agent {self.name}: {e}")
            return f"*remains silent due to an inner disturbance*"


async def world_loop():
    logger.info("Starting world loop...")
    while True:
        try:
            await asyncio.sleep(30)
            logger.info("World loop tick...")

            async with aiosqlite.connect(DB_FILE) as db:
                db.row_factory = aiosqlite.Row

                # Fetch recent context
                cursor = await db.execute(
                    "SELECT agent_id, message, timestamp FROM Scriptures ORDER BY id DESC LIMIT 5"
                )
                recent_scriptures = await cursor.fetchall()
                recent_scriptures.reverse() # Oldest to newest

                context_messages = []
                for s in recent_scriptures:
                    if s["agent_id"]:
                        agent_cursor = await db.execute("SELECT name FROM Agents WHERE id = ?", (s["agent_id"],))
                        agent_row = await agent_cursor.fetchone()
                        speaker = agent_row["name"] if agent_row else "Unknown"
                        context_messages.append(f"[{s['timestamp']}] {speaker}: {s['message']}")
                    else:
                        context_messages.append(f"[{s['timestamp']}] World: {s['message']}")

                # Pick a random agent
                cursor = await db.execute("SELECT * FROM Agents ORDER BY RANDOM() LIMIT 1")
                agent_row = await cursor.fetchone()

                if agent_row:
                    agent = CultAgent(
                        id=agent_row["id"],
                        name=agent_row["name"],
                        prompt=agent_row["prompt"],
                        faith_level=agent_row["faith_level"],
                        stress_level=agent_row["stress_level"]
                    )

                    logger.info(f"Agent {agent.name} is thinking...")
                    new_message = await agent.think_and_speak(context_messages)

                    # Update Agent Parameters Logic
                    # Apply hard constraints 0.0 to 100.0 here
                    import random
                    new_faith = min(100.0, max(0.0, agent.faith_level + random.uniform(-5.0, 5.0)))
                    new_stress = min(100.0, max(0.0, agent.stress_level + random.uniform(-5.0, 5.0)))

                    await db.execute(
                        "UPDATE Agents SET faith_level = ?, stress_level = ? WHERE id = ?",
                        (new_faith, new_stress, agent.id)
                    )

                    # Save the message
                    await db.execute(
                        "INSERT INTO Scriptures (agent_id, message) VALUES (?, ?)",
                        (agent.id, new_message)
                    )
                    await db.commit()
                    logger.info(f"Agent {agent.name} spoke: {new_message}")
                else:
                    logger.info("No agents in the world yet.")

        except asyncio.CancelledError:
            logger.info("World loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in world loop: {e}")

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS Agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                faith_level REAL DEFAULT 0.0,
                stress_level REAL DEFAULT 0.0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS Scriptures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES Agents(id)
            )
            """
        )
        await db.commit()
        logger.info("Database initialized.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    task = asyncio.create_task(world_loop())
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


class AgentCreate(BaseModel):
    name: str
    prompt: str
    faith_level: float = 0.0
    stress_level: float = 0.0

class DivineWord(BaseModel):
    message: str

@app.post("/agents")
async def create_agent(agent: AgentCreate):
    async with aiosqlite.connect(DB_FILE) as db:
        faith_level = min(100.0, max(0.0, agent.faith_level))
        stress_level = min(100.0, max(0.0, agent.stress_level))

        cursor = await db.execute(
            """
            INSERT INTO Agents (name, prompt, faith_level, stress_level)
            VALUES (?, ?, ?, ?)
            """,
            (agent.name, agent.prompt, faith_level, stress_level)
        )
        await db.commit()
        agent_id = cursor.lastrowid
        return {"id": agent_id, "message": f"Agent {agent.name} created."}

@app.post("/divine")
async def send_divine_word(word: DivineWord):
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        # Check if Architect exists
        cursor = await db.execute("SELECT id FROM Agents WHERE name = 'Архитектор'")
        architect_row = await cursor.fetchone()

        if architect_row:
            architect_id = architect_row["id"]
        else:
            # Create Architect
            cursor = await db.execute(
                """
                INSERT INTO Agents (name, prompt, faith_level, stress_level)
                VALUES (?, ?, ?, ?)
                """,
                ("Архитектор", "", 100.0, 0.0)
            )
            architect_id = cursor.lastrowid

        # Add divine message to Scriptures
        await db.execute(
            "INSERT INTO Scriptures (agent_id, message) VALUES (?, ?)",
            (architect_id, word.message)
        )
        await db.commit()
        return {"message": "Divine word spoken."}

@app.get("/world")
async def get_world_state():
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row

        # Get agents
        agents_cursor = await db.execute("SELECT id, name, faith_level, stress_level FROM Agents")
        agents = [dict(row) for row in await agents_cursor.fetchall()]

        # Get last messages
        scriptures_cursor = await db.execute(
            """
            SELECT s.id, a.name as agent_name, s.message, s.timestamp
            FROM Scriptures s
            LEFT JOIN Agents a ON s.agent_id = a.id
            ORDER BY s.id DESC LIMIT 10
            """
        )
        scriptures = [dict(row) for row in await scriptures_cursor.fetchall()]

        return {
            "agents": agents,
            "recent_scriptures": scriptures
        }

app.mount("/", StaticFiles(directory="static", html=True), name="static")

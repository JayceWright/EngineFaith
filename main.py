import asyncio
import logging
from contextlib import asynccontextmanager

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

import aiosqlite
from fastapi import FastAPI
from pydantic import BaseModel
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DB_FILE = "faith_engine.db"

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
        system_prompt = (
            f"You are {self.name}, an AI agent in a simulated world. "
            f"Your personality/prompt: {self.prompt}. "
            f"Your current faith level is {self.faith_level} and stress level is {self.stress_level}. "
            "You are participating in a cult simulation. Based on the recent events/messages in the world, "
            "generate a short, new message or action (1-3 sentences) that reflects your beliefs and current state."
        )

        user_content = "Recent world events/messages:\n"
        if context_messages:
            for i, msg in enumerate(context_messages, 1):
                user_content += f"{i}. {msg}\n"
        else:
            user_content += "The world is quiet. Nothing has happened yet.\n"

        user_content += "\nWhat do you say or do next?"

        try:
            response = await openai_client.chat.completions.create(
                model="openrouter/free", # Using the specified free model from openrouter
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=150,
                temperature=0.7
            )
            logger.info(f"DEBUG - Raw API Response: {response}")
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

@app.post("/agents")
async def create_agent(agent: AgentCreate):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            """
            INSERT INTO Agents (name, prompt, faith_level, stress_level)
            VALUES (?, ?, ?, ?)
            """,
            (agent.name, agent.prompt, agent.faith_level, agent.stress_level)
        )
        await db.commit()
        agent_id = cursor.lastrowid
        return {"id": agent_id, "message": f"Agent {agent.name} created."}

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

@app.get("/")
async def root():
    return {"message": "Welcome to the Engine of Faith"}

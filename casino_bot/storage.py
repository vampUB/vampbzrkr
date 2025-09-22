"""Async storage layer for the casino bot."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import aiosqlite


@dataclass(slots=True)
class User:
    telegram_id: int
    username: Optional[str]
    balance: int
    created_at: datetime


@dataclass(slots=True)
class Transaction:
    id: int
    user_id: int
    type: str
    amount: int
    meta: Dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class GameRound:
    id: int
    user_id: int
    game: str
    bet: int
    payout: int
    state: Dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class UserStats:
    user_id: int
    xp: int
    total_wagered: int
    total_won: int
    games_played: int
    wins: int
    losses: int
    biggest_win: int


@dataclass(slots=True)
class GameStats:
    user_id: int
    game: str
    games_played: int
    total_wagered: int
    total_won: int


@dataclass(slots=True)
class Achievement:
    id: int
    code: str
    title: str
    description: str
    threshold: int
    metric: str


@dataclass(slots=True)
class UserAchievement:
    achievement: Achievement
    unlocked_at: datetime


@dataclass(slots=True)
class Mission:
    id: int
    code: str
    title: str
    description: str
    target: int
    reward: int
    metric: str
    frequency: str


@dataclass(slots=True)
class UserMission:
    mission: Mission
    progress: int
    completed_at: Optional[datetime]
    claimed_at: Optional[datetime]


class CasinoStorage:
    """SQLite-based storage facade."""

    def __init__(self, database_path: str) -> None:
        if database_path.startswith("sqlite+aiosqlite:///"):
            database_path = database_path.replace("sqlite+aiosqlite:///", "", 1)
        self._db_path = Path(database_path)
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        if self._connection is None:
            self._connection = await aiosqlite.connect(self._db_path)
            self._connection.row_factory = aiosqlite.Row
            await self._initialise()

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def _initialise(self) -> None:
        assert self._connection is not None
        await self._connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                meta TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(telegram_id)
            );
            CREATE TABLE IF NOT EXISTS game_rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                bet INTEGER NOT NULL,
                payout INTEGER NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(telegram_id)
            );
            CREATE TABLE IF NOT EXISTS daily_bonus (
                user_id INTEGER PRIMARY KEY,
                last_claimed_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(telegram_id)
            );
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER NOT NULL DEFAULT 0,
                total_wagered INTEGER NOT NULL DEFAULT 0,
                total_won INTEGER NOT NULL DEFAULT 0,
                games_played INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                biggest_win INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(telegram_id)
            );
            CREATE TABLE IF NOT EXISTS user_game_stats (
                user_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                games_played INTEGER NOT NULL DEFAULT 0,
                total_wagered INTEGER NOT NULL DEFAULT 0,
                total_won INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(user_id, game),
                FOREIGN KEY(user_id) REFERENCES users(telegram_id)
            );
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                threshold INTEGER NOT NULL,
                metric TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at TEXT NOT NULL,
                PRIMARY KEY(user_id, achievement_id),
                FOREIGN KEY(user_id) REFERENCES users(telegram_id),
                FOREIGN KEY(achievement_id) REFERENCES achievements(id)
            );
            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                target INTEGER NOT NULL,
                reward INTEGER NOT NULL,
                metric TEXT NOT NULL,
                frequency TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_missions (
                user_id INTEGER NOT NULL,
                mission_id INTEGER NOT NULL,
                progress INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                claimed_at TEXT,
                PRIMARY KEY(user_id, mission_id),
                FOREIGN KEY(user_id) REFERENCES users(telegram_id),
                FOREIGN KEY(mission_id) REFERENCES missions(id)
            );
            """
        )
        await self._connection.commit()
        await self._seed_reference_data()

    async def _seed_reference_data(self) -> None:
        conn = await self._require_connection()
        achievements = [
            (
                "first_win",
                "Первый выигрыш",
                "Завершите игру с положительным результатом",
                1,
                "wins",
            ),
            (
                "loyal_player",
                "Постоянный игрок",
                "Сыграйте 50 раундов в любых играх",
                50,
                "games_played",
            ),
            (
                "high_roller",
                "Хайроллер",
                "Поставьте суммарно 25 000 чипов",
                25_000,
                "total_wagered",
            ),
            (
                "big_win",
                "Крупный куш",
                "Выиграйте за один раунд более 5 000 чипов",
                5_000,
                "biggest_win",
            ),
        ]
        for code, title, desc, threshold, metric in achievements:
            await conn.execute(
                """
                INSERT OR IGNORE INTO achievements (code, title, description, threshold, metric)
                VALUES (?, ?, ?, ?, ?)
                """,
                (code, title, desc, threshold, metric),
            )

        missions = [
            (
                "daily_games",
                "Играй каждый день",
                "Сыграть 5 любых раундов за сутки",
                5,
                200,
                "games_played",
                "daily",
            ),
            (
                "daily_wager",
                "Оборот дня",
                "Поставить 2 000 чипов за сутки",
                2_000,
                300,
                "total_wagered",
                "daily",
            ),
            (
                "weekly_wins",
                "Неделя побед",
                "Выиграть суммарно 7 500 чипов за неделю",
                7_500,
                600,
                "total_won",
                "weekly",
            ),
        ]
        for code, title, desc, target, reward, metric, frequency in missions:
            await conn.execute(
                """
                INSERT OR IGNORE INTO missions (code, title, description, target, reward, metric, frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (code, title, desc, target, reward, metric, frequency),
            )

        await conn.commit()

    async def get_user(self, telegram_id: int) -> Optional[User]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            "SELECT telegram_id, username, balance, created_at FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return User(
            telegram_id=row["telegram_id"],
            username=row["username"],
            balance=row["balance"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    async def create_user(self, telegram_id: int, username: Optional[str], bonus: int) -> User:
        conn = await self._require_connection()
        now = datetime.utcnow().isoformat()
        await conn.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, balance, created_at) VALUES (?, ?, ?, ?)",
            (telegram_id, username, bonus, now),
        )
        await conn.execute(
            "INSERT OR REPLACE INTO daily_bonus (user_id, last_claimed_at) VALUES (?, ?)",
            (telegram_id, (datetime.utcnow() - timedelta(days=1, seconds=1)).isoformat()),
        )
        await conn.execute(
            "INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)",
            (telegram_id,),
        )
        await conn.execute(
            """
            INSERT OR IGNORE INTO user_missions (user_id, mission_id)
            SELECT ?, id FROM missions
            """,
            (telegram_id,),
        )
        await conn.commit()
        user = await self.get_user(telegram_id)
        assert user is not None
        return user

    async def update_balance(self, telegram_id: int, delta: int) -> int:
        conn = await self._require_connection()
        await conn.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (delta, telegram_id),
        )
        await conn.commit()
        user = await self.get_user(telegram_id)
        if user is None:
            raise ValueError("User not found after balance update")
        return user.balance

    async def set_balance(self, telegram_id: int, amount: int) -> None:
        conn = await self._require_connection()
        await conn.execute(
            "UPDATE users SET balance = ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )
        await conn.commit()

    async def record_transaction(
        self, telegram_id: int, type_: str, amount: int, meta: Optional[Dict[str, Any]] = None
    ) -> Transaction:
        conn = await self._require_connection()
        now = datetime.utcnow().isoformat()
        cursor = await conn.execute(
            """
            INSERT INTO transactions (user_id, type, amount, meta, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, type_, amount, json.dumps(meta or {}), now),
        )
        await conn.commit()
        transaction_id = cursor.lastrowid
        return Transaction(
            id=transaction_id,
            user_id=telegram_id,
            type=type_,
            amount=amount,
            meta=meta or {},
            created_at=datetime.fromisoformat(now),
        )

    async def record_game_round(
        self,
        telegram_id: int,
        game: str,
        bet: int,
        payout: int,
        state: Dict[str, Any],
    ) -> GameRound:
        conn = await self._require_connection()
        now = datetime.utcnow().isoformat()
        cursor = await conn.execute(
            """
            INSERT INTO game_rounds (user_id, game, bet, payout, state, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (telegram_id, game, bet, payout, json.dumps(state), now),
        )
        await conn.commit()
        return GameRound(
            id=cursor.lastrowid,
            user_id=telegram_id,
            game=game,
            bet=bet,
            payout=payout,
            state=state,
            created_at=datetime.fromisoformat(now),
        )

    async def get_recent_transactions(self, telegram_id: int, limit: int = 5) -> Sequence[Transaction]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT id, user_id, type, amount, meta, created_at
            FROM transactions WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (telegram_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [
            Transaction(
                id=row["id"],
                user_id=row["user_id"],
                type=row["type"],
                amount=row["amount"],
                meta=json.loads(row["meta"] or "{}"),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def get_recent_games(self, telegram_id: int, limit: int = 5) -> Sequence[GameRound]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT id, user_id, game, bet, payout, state, created_at
            FROM game_rounds WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (telegram_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [
            GameRound(
                id=row["id"],
                user_id=row["user_id"],
                game=row["game"],
                bet=row["bet"],
                payout=row["payout"],
                state=json.loads(row["state"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def get_leaderboard(self, limit: int = 10, days: int = 7) -> Sequence[Dict[str, Any]]:
        conn = await self._require_connection()
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cursor = await conn.execute(
            """
            SELECT u.telegram_id, u.username, SUM(gr.payout) as winnings
            FROM game_rounds gr
            JOIN users u ON u.telegram_id = gr.user_id
            WHERE gr.created_at >= ? AND gr.payout > 0
            GROUP BY gr.user_id
            ORDER BY winnings DESC
            LIMIT ?
            """,
            (since, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]

    async def get_daily_bonus_timestamp(self, telegram_id: int) -> Optional[datetime]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            "SELECT last_claimed_at FROM daily_bonus WHERE user_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None or row["last_claimed_at"] is None:
            return None
        return datetime.fromisoformat(row["last_claimed_at"])

    async def set_daily_bonus_timestamp(self, telegram_id: int, timestamp: datetime) -> None:
        conn = await self._require_connection()
        await conn.execute(
            "INSERT OR REPLACE INTO daily_bonus (user_id, last_claimed_at) VALUES (?, ?)",
            (telegram_id, timestamp.isoformat()),
        )
        await conn.commit()

    async def ensure_user_stats(self, telegram_id: int) -> UserStats:
        conn = await self._require_connection()
        await conn.execute(
            "INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)",
            (telegram_id,),
        )
        await conn.execute(
            """
            INSERT OR IGNORE INTO user_missions (user_id, mission_id)
            SELECT ?, id FROM missions
            """,
            (telegram_id,),
        )
        await conn.commit()
        stats = await self.get_user_stats(telegram_id)
        if stats is None:
            raise ValueError("Failed to ensure user stats")
        return stats

    async def get_user_stats(self, telegram_id: int) -> Optional[UserStats]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT user_id, xp, total_wagered, total_won, games_played, wins, losses, biggest_win
            FROM user_stats WHERE user_id = ?
            """,
            (telegram_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return UserStats(
            user_id=row["user_id"],
            xp=row["xp"],
            total_wagered=row["total_wagered"],
            total_won=row["total_won"],
            games_played=row["games_played"],
            wins=row["wins"],
            losses=row["losses"],
            biggest_win=row["biggest_win"],
        )

    async def get_user_game_stats(self, telegram_id: int) -> Sequence[GameStats]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT user_id, game, games_played, total_wagered, total_won
            FROM user_game_stats WHERE user_id = ?
            ORDER BY game
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [
            GameStats(
                user_id=row["user_id"],
                game=row["game"],
                games_played=row["games_played"],
                total_wagered=row["total_wagered"],
                total_won=row["total_won"],
            )
            for row in rows
        ]

    async def update_stats_after_round(
        self, telegram_id: int, game: str, bet: int, payout: int
    ) -> Tuple[UserStats, GameStats]:
        conn = await self._require_connection()
        await conn.execute(
            "INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)",
            (telegram_id,),
        )
        await conn.execute(
            "INSERT OR IGNORE INTO user_game_stats (user_id, game) VALUES (?, ?)",
            (telegram_id, game),
        )
        xp_gain = max(1, bet // 10)
        net_win = max(0, payout - bet)
        if net_win:
            xp_gain += max(1, net_win // 20)
        wins = 1 if payout > bet else 0
        losses = 1 if payout < bet else 0
        await conn.execute(
            """
            UPDATE user_stats
            SET xp = xp + ?,
                total_wagered = total_wagered + ?,
                total_won = total_won + ?,
                games_played = games_played + 1,
                wins = wins + ?,
                losses = losses + ?,
                biggest_win = CASE WHEN ? > biggest_win THEN ? ELSE biggest_win END
            WHERE user_id = ?
            """,
            (xp_gain, bet, payout, wins, losses, net_win, net_win, telegram_id),
        )
        await conn.execute(
            """
            UPDATE user_game_stats
            SET games_played = games_played + 1,
                total_wagered = total_wagered + ?,
                total_won = total_won + ?
            WHERE user_id = ? AND game = ?
            """,
            (bet, payout, telegram_id, game),
        )
        await conn.commit()
        stats = await self.get_user_stats(telegram_id)
        game_stats = await self._get_single_game_stats(telegram_id, game)
        if stats is None or game_stats is None:
            raise ValueError("Failed to load stats after update")
        return stats, game_stats

    async def _get_single_game_stats(self, telegram_id: int, game: str) -> Optional[GameStats]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT user_id, game, games_played, total_wagered, total_won
            FROM user_game_stats WHERE user_id = ? AND game = ?
            """,
            (telegram_id, game),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return GameStats(
            user_id=row["user_id"],
            game=row["game"],
            games_played=row["games_played"],
            total_wagered=row["total_wagered"],
            total_won=row["total_won"],
        )

    async def list_user_achievements(self, telegram_id: int) -> Sequence[UserAchievement]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT a.id, a.code, a.title, a.description, a.threshold, a.metric,
                   ua.unlocked_at
            FROM achievements a
            LEFT JOIN user_achievements ua
                ON ua.achievement_id = a.id AND ua.user_id = ?
            ORDER BY a.id
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        achievements: List[UserAchievement] = []
        for row in rows:
            achievement = Achievement(
                id=row["id"],
                code=row["code"],
                title=row["title"],
                description=row["description"],
                threshold=row["threshold"],
                metric=row["metric"],
            )
            if row["unlocked_at"]:
                achievements.append(
                    UserAchievement(
                        achievement=achievement,
                        unlocked_at=datetime.fromisoformat(row["unlocked_at"]),
                    )
                )
        return achievements

    async def evaluate_achievements(
        self, telegram_id: int, stats: UserStats
    ) -> Sequence[UserAchievement]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT a.id, a.code, a.title, a.description, a.threshold, a.metric,
                   ua.unlocked_at
            FROM achievements a
            LEFT JOIN user_achievements ua
                ON ua.achievement_id = a.id AND ua.user_id = ?
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        unlocked: List[UserAchievement] = []
        metrics = {
            "wins": stats.wins,
            "games_played": stats.games_played,
            "total_wagered": stats.total_wagered,
            "total_won": stats.total_won,
            "biggest_win": stats.biggest_win,
        }
        now_iso = datetime.utcnow().isoformat()
        for row in rows:
            if row["unlocked_at"]:
                continue
            metric = row["metric"]
            if metrics.get(metric, 0) >= row["threshold"]:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, unlocked_at)
                    VALUES (?, ?, ?)
                    """,
                    (telegram_id, row["id"], now_iso),
                )
                unlocked.append(
                    UserAchievement(
                        achievement=Achievement(
                            id=row["id"],
                            code=row["code"],
                            title=row["title"],
                            description=row["description"],
                            threshold=row["threshold"],
                            metric=row["metric"],
                        ),
                        unlocked_at=datetime.fromisoformat(now_iso),
                    )
                )
        if unlocked:
            await conn.commit()
        return unlocked

    async def ensure_user_missions(self, telegram_id: int) -> None:
        conn = await self._require_connection()
        await conn.execute(
            """
            INSERT OR IGNORE INTO user_missions (user_id, mission_id)
            SELECT ?, id FROM missions
            """,
            (telegram_id,),
        )
        await conn.commit()

    async def get_user_missions(self, telegram_id: int) -> Sequence[UserMission]:
        conn = await self._require_connection()
        await self.ensure_user_missions(telegram_id)
        cursor = await conn.execute(
            """
            SELECT m.id, m.code, m.title, m.description, m.target, m.reward, m.metric, m.frequency,
                   um.progress, um.completed_at, um.claimed_at
            FROM user_missions um
            JOIN missions m ON m.id = um.mission_id
            WHERE um.user_id = ?
            ORDER BY m.frequency, m.id
            """,
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        missions: List[UserMission] = []
        for row in rows:
            missions.append(
                UserMission(
                    mission=Mission(
                        id=row["id"],
                        code=row["code"],
                        title=row["title"],
                        description=row["description"],
                        target=row["target"],
                        reward=row["reward"],
                        metric=row["metric"],
                        frequency=row["frequency"],
                    ),
                    progress=row["progress"],
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    claimed_at=datetime.fromisoformat(row["claimed_at"]) if row["claimed_at"] else None,
                )
            )
        return missions

    async def advance_missions(
        self, telegram_id: int, updates: Dict[str, int]
    ) -> Sequence[UserMission]:
        if not updates:
            return []
        conn = await self._require_connection()
        await self.ensure_user_missions(telegram_id)
        completed: List[UserMission] = []
        now_iso = datetime.utcnow().isoformat()
        for metric, amount in updates.items():
            if amount <= 0:
                continue
            cursor = await conn.execute(
                """
                SELECT m.id, m.code, m.title, m.description, m.target, m.reward, m.metric, m.frequency,
                       um.progress, um.completed_at, um.claimed_at
                FROM user_missions um
                JOIN missions m ON m.id = um.mission_id
                WHERE um.user_id = ? AND m.metric = ?
                """,
                (telegram_id, metric),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            for row in rows:
                progress = row["progress"]
                if row["completed_at"]:
                    continue
                new_progress = min(progress + amount, row["target"])
                completed_now = new_progress >= row["target"]
                await conn.execute(
                    """
                    UPDATE user_missions
                    SET progress = ?,
                        completed_at = CASE WHEN ? = 1 THEN COALESCE(completed_at, ?) ELSE completed_at END
                    WHERE user_id = ? AND mission_id = ?
                    """,
                    (new_progress, 1 if completed_now else 0, now_iso, telegram_id, row["id"]),
                )
                if completed_now:
                    completed.append(
                        UserMission(
                            mission=Mission(
                                id=row["id"],
                                code=row["code"],
                                title=row["title"],
                                description=row["description"],
                                target=row["target"],
                                reward=row["reward"],
                                metric=row["metric"],
                                frequency=row["frequency"],
                            ),
                            progress=new_progress,
                            completed_at=datetime.fromisoformat(now_iso),
                            claimed_at=None,
                        )
                    )
        if completed:
            await conn.commit()
        else:
            # ensure progress updates flushed even if no missions were completed
            await conn.commit()
        return completed

    async def claim_mission_reward(self, telegram_id: int, code: str) -> Tuple[Mission, bool]:
        conn = await self._require_connection()
        cursor = await conn.execute(
            """
            SELECT m.id, m.code, m.title, m.description, m.target, m.reward, m.metric, m.frequency,
                   um.progress, um.completed_at, um.claimed_at
            FROM missions m
            JOIN user_missions um ON um.mission_id = m.id
            WHERE um.user_id = ? AND m.code = ?
            """,
            (telegram_id, code),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            raise ValueError("Mission not found")
        mission = Mission(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            description=row["description"],
            target=row["target"],
            reward=row["reward"],
            metric=row["metric"],
            frequency=row["frequency"],
        )
        if not row["completed_at"]:
            raise ValueError("Mission not completed yet")
        if row["claimed_at"]:
            return mission, False
        now_iso = datetime.utcnow().isoformat()
        await conn.execute(
            "UPDATE user_missions SET claimed_at = ? WHERE user_id = ? AND mission_id = ?",
            (now_iso, telegram_id, row["id"]),
        )
        await conn.commit()
        return mission, True

    async def _require_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            await self.connect()
        assert self._connection is not None
        return self._connection


__all__ = [
    "CasinoStorage",
    "User",
    "Transaction",
    "GameRound",
    "UserStats",
    "GameStats",
    "Achievement",
    "UserAchievement",
    "Mission",
    "UserMission",
]

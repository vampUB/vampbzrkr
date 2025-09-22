"""Player progression, achievements and missions management."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

from ..storage import (
    CasinoStorage,
    GameStats,
    Mission,
    UserAchievement,
    UserMission,
    UserStats,
)


@dataclass(slots=True)
class LoyaltyTier:
    name: str
    wager_requirement: int
    bonus_multiplier: float


@dataclass(slots=True)
class ProgressionUpdate:
    stats: UserStats
    game_stats: GameStats
    level: int
    xp_to_next: int
    loyalty_tier: LoyaltyTier
    unlocked_achievements: Sequence[UserAchievement]
    completed_missions: Sequence[UserMission]


@dataclass(slots=True)
class ProfileOverview:
    stats: UserStats
    level: int
    xp_to_next: int
    loyalty_tier: LoyaltyTier
    game_stats: Sequence[GameStats]
    achievements: Sequence[UserAchievement]
    missions: Sequence[UserMission]


class ProgressionService:
    """High-level API for user stats, achievements and missions."""

    def __init__(self, storage: CasinoStorage) -> None:
        self.storage = storage
        self._tiers = (
            LoyaltyTier("Bronze", 0, 1.0),
            LoyaltyTier("Silver", 5_000, 1.05),
            LoyaltyTier("Gold", 25_000, 1.1),
            LoyaltyTier("Platinum", 75_000, 1.2),
            LoyaltyTier("Diamond", 150_000, 1.35),
        )

    async def get_profile(self, user_id: int) -> ProfileOverview:
        stats = await self.storage.ensure_user_stats(user_id)
        game_stats = await self.storage.get_user_game_stats(user_id)
        achievements = await self.storage.list_user_achievements(user_id)
        missions = await self.storage.get_user_missions(user_id)
        level, xp_to_next = self._level_from_xp(stats.xp)
        tier = self._tier_from_wager(stats.total_wagered)
        return ProfileOverview(
            stats=stats,
            level=level,
            xp_to_next=xp_to_next,
            loyalty_tier=tier,
            game_stats=game_stats,
            achievements=achievements,
            missions=missions,
        )

    async def record_round(
        self, user_id: int, game: str, bet: int, payout: int
    ) -> ProgressionUpdate:
        stats, game_stats = await self.storage.update_stats_after_round(
            user_id, game, bet, payout
        )
        level, xp_to_next = self._level_from_xp(stats.xp)
        tier = self._tier_from_wager(stats.total_wagered)
        unlocked = await self.storage.evaluate_achievements(user_id, stats)
        mission_updates: Dict[str, int] = {
            "games_played": 1,
            "total_wagered": bet,
            "total_won": payout,
        }
        if payout > bet:
            mission_updates["wins"] = mission_updates.get("wins", 0) + 1
        completed = await self.storage.advance_missions(user_id, mission_updates)
        return ProgressionUpdate(
            stats=stats,
            game_stats=game_stats,
            level=level,
            xp_to_next=xp_to_next,
            loyalty_tier=tier,
            unlocked_achievements=unlocked,
            completed_missions=completed,
        )

    async def claim_mission(self, user_id: int, code: str) -> Tuple[Mission, bool]:
        return await self.storage.claim_mission_reward(user_id, code)

    def _level_from_xp(self, xp: int) -> Tuple[int, int]:
        level = 1
        threshold = 200
        remaining = xp
        while remaining >= threshold:
            remaining -= threshold
            level += 1
            threshold = 200 + (level - 1) * 150
        xp_to_next = max(threshold - remaining, 0)
        return level, xp_to_next

    def _tier_from_wager(self, total_wagered: int) -> LoyaltyTier:
        tier = self._tiers[0]
        for candidate in self._tiers:
            if total_wagered >= candidate.wager_requirement:
                tier = candidate
            else:
                break
        return tier


__all__ = [
    "LoyaltyTier",
    "ProgressionService",
    "ProgressionUpdate",
    "ProfileOverview",
]

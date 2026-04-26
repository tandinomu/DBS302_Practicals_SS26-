import redis
from typing import List, Dict, Optional, Tuple

"""
Mini Case Study: Key Schema Design
------------------------------------
Global leaderboard:       leaderboard:quiz:global
Country leaderboard:      leaderboard:quiz:country:{country_code}

Examples:
  leaderboard:quiz:country:BT   (Bhutan)
  leaderboard:quiz:country:IN   (India)
  leaderboard:quiz:country:US   (United States)
"""

class QuizLeaderboard:
    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        self.r = redis_client or redis.Redis(
            host="127.0.0.1", port=6379, db=0, decode_responses=True
        )
        self.global_key = "leaderboard:quiz:global"

    def _country_key(self, country_code: str) -> str:
        """Build country-specific leaderboard key."""
        return f"leaderboard:quiz:country:{country_code.upper()}"

    def add_score(self, player_id: str, score: float, country_code: str) -> None:
        """
        Add score to both global and country-specific leaderboard.
        This keeps both in sync automatically.
        """
        self.r.zadd(self.global_key, {player_id: score})
        self.r.zadd(self._country_key(country_code), {player_id: score})

    def get_global_top(self, n: int = 10) -> List[Dict]:
        """Get top N players globally."""
        results = self.r.zrevrange(self.global_key, 0, n - 1, withscores=True)
        return [
            {"rank": i + 1, "player": player, "score": score}
            for i, (player, score) in enumerate(results)
        ]

    def get_country_top(self, country_code: str, n: int = 10) -> List[Dict]:
        """Get top N players for a specific country."""
        key = self._country_key(country_code)
        results = self.r.zrevrange(key, 0, n - 1, withscores=True)
        return [
            {"rank": i + 1, "player": player, "score": score}
            for i, (player, score) in enumerate(results)
        ]

    def get_country_rank(self, player_id: str, country_code: str) -> Optional[int]:
        """Get a player's rank within their country."""
        key = self._country_key(country_code)
        rank = self.r.zrevrank(key, player_id)
        return rank + 1 if rank is not None else None

    def get_global_rank(self, player_id: str) -> Optional[int]:
        """Get a player's global rank."""
        rank = self.r.zrevrank(self.global_key, player_id)
        return rank + 1 if rank is not None else None


def demo():
    lb = QuizLeaderboard()

    # Clear old data
    lb.r.delete(lb.global_key)
    lb.r.delete(lb._country_key("BT"))
    lb.r.delete(lb._country_key("IN"))

    print("Adding quiz scores...")
    lb.add_score("tenzin",  950, "BT")
    lb.add_score("dorji",   870, "BT")
    lb.add_score("pema",    910, "BT")
    lb.add_score("rahul",   980, "IN")
    lb.add_score("priya",   930, "IN")
    lb.add_score("amit",    860, "IN")

    print("\n--- Global Top 5 ---")
    for entry in lb.get_global_top(5):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    print("\n--- Bhutan (BT) Top 3 ---")
    for entry in lb.get_country_top("BT", 3):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    print("\n--- India (IN) Top 3 ---")
    for entry in lb.get_country_top("IN", 3):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    print("\n--- Individual Rankings ---")
    print(f" Tenzin - Global Rank: #{lb.get_global_rank('tenzin')}, BT Rank: #{lb.get_country_rank('tenzin', 'BT')}")
    print(f" Rahul  - Global Rank: #{lb.get_global_rank('rahul')},  IN Rank: #{lb.get_country_rank('rahul', 'IN')}")


if __name__ == "__main__":
    demo()
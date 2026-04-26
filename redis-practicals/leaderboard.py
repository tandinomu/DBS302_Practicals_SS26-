import redis
from typing import List, Dict, Optional, Tuple

class Leaderboard:
    """
    Leaderboard backed by Redis sorted sets.
    Encapsulates all leaderboard-related operations.
    """

    def __init__(self, name: str, redis_client: Optional[redis.Redis] = None) -> None:
        self.name = name
        self.key = f"leaderboard:{name}"
        self.r = redis_client or redis.Redis(
            host="127.0.0.1",
            port=6379,
            db=0,
            decode_responses=True,
        )

    def add_score(self, player_id: str, score: float) -> int:
        """
        Add or update a player's score.
        Returns the player's new rank (1-based).
        """
        # ZADD will insert or update the member's score
        self.r.zadd(self.key, {player_id: score})
        return self.get_rank(player_id)

    def increment_score(self, player_id: str, delta: float) -> Tuple[float, int]:
        """
        Increment a player's score.
        Returns (new_score, new_rank).
        """
        new_score = self.r.zincrby(self.key, delta, player_id)
        new_rank = self.get_rank(player_id)
        return new_score, new_rank

    def get_rank(self, player_id: str) -> Optional[int]:
        """
        Get player's rank (1-based). Returns None if player is not found.
        """
        rank_zero_based = self.r.zrevrank(self.key, player_id)
        if rank_zero_based is None:
            return None
        # Convert 0-based rank to 1-based
        return rank_zero_based + 1

    def get_score(self, player_id: str) -> Optional[float]:
        """
        Get player's current score.
        """
        score = self.r.zscore(self.key, player_id)
        return float(score) if score is not None else None

    def get_top(self, n: int = 10) -> List[Dict]:
        """
        Get top N players.
        """
        results = self.r.zrevrange(self.key, 0, n - 1, withscores=True)
        return [
            {"rank": i + 1, "player": player, "score": score}
            for i, (player, score) in enumerate(results)
        ]

    def get_page(self, page: int, page_size: int = 10) -> List[Dict]:
        """
        Get a specific page of the leaderboard.
        Page is 1-based.
        """
        if page < 1:
            raise ValueError("page must be >= 1")

        start = (page - 1) * page_size
        end = start + page_size - 1
        results = self.r.zrevrange(self.key, start, end, withscores=True)
        return [
            {"rank": start + i + 1, "player": player, "score": score}
            for i, (player, score) in enumerate(results)
        ]

    def get_around_player(self, player_id: str, radius: int = 2) -> List[Dict]:
        """
        Get players around a specific player (for 'around me' views).
        Includes 'radius' players above and below the given player.
        """
        rank_zero_based = self.r.zrevrank(self.key, player_id)
        if rank_zero_based is None:
            return []

        start = max(0, rank_zero_based - radius)
        end = rank_zero_based + radius
        results = self.r.zrevrange(self.key, start, end, withscores=True)

        return [
            {"rank": start + i + 1, "player": player, "score": score}
            for i, (player, score) in enumerate(results)
        ]

    def count_players(self) -> int:
        """
        Get total number of players in the leaderboard.
        """
        return self.r.zcard(self.key)

    def remove_player(self, player_id: str) -> bool:
        """
        Remove a player from the leaderboard.
        Returns True if the player was removed, False otherwise.
        """
        removed = self.r.zrem(self.key, player_id)
        return removed > 0
    
    def get_players_in_score_range(self, min_score: float, max_score: float) -> List[Dict]:
        """Exercise 2: Get players within a score range using ZREVRANGEBYSCORE."""
        results = self.r.zrevrangebyscore(self.key, max_score, min_score, withscores=True)
        return [
            {"player": player, "score": score}
            for player, score in results
        ]

    def set_daily_ttl(self, days: int = 7) -> None:
        """Exercise 3: Set TTL on the leaderboard key to expire after given days."""
        self.r.expire(self.key, days * 24 * 60 * 60)


def demo():
    # ---------- Original demo ----------
    lb = Leaderboard("game:season1")
    lb.r.delete(lb.key)

    print("Adding initial scores...")
    lb.add_score("alice", 1500)
    lb.add_score("bob", 2300)
    lb.add_score("charlie", 1800)
    lb.add_score("diana", 2100)
    lb.add_score("eve", 1950)

    print("\nTop 3 players:")
    for entry in lb.get_top(3):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    print("\nCharlie's current rank and score:")
    print(" Rank:", lb.get_rank("charlie"))
    print(" Score:", lb.get_score("charlie"))

    print("\nIncrementing Charlie's score by 500...")
    new_score, new_rank = lb.increment_score("charlie", 500)
    print(f" New score: {new_score}, new rank: {new_rank}")

    print("\nPlayers around Charlie:")
    for entry in lb.get_around_player("charlie", radius=2):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    print("\nPage 1 of leaderboard (page_size=3):")
    for entry in lb.get_page(page=1, page_size=3):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    # ---------- Exercise 1: Daily and All-Time leaderboards ----------
    print("\n--- Exercise 1: Daily and All-Time Leaderboards ---")

    daily_lb = Leaderboard("game:daily:2026-03-17")
    alltime_lb = Leaderboard("game:alltime")

    daily_lb.r.delete(daily_lb.key)
    alltime_lb.r.delete(alltime_lb.key)

    # Add same players to both
    for lb_instance in [daily_lb, alltime_lb]:
        lb_instance.add_score("alice", 1500)
        lb_instance.add_score("bob", 2300)
        lb_instance.add_score("charlie", 2300)
        lb_instance.add_score("diana", 2100)
        lb_instance.add_score("eve", 1950)

    print("\nDaily Leaderboard Top 3:")
    for entry in daily_lb.get_top(3):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    print("\nAll-Time Leaderboard Top 3:")
    for entry in alltime_lb.get_top(3):
        print(f" #{entry['rank']} {entry['player']}: {entry['score']}")

    # ---------- Exercise 2: Score range query ----------
    print("\n--- Exercise 2: Players with scores between 1800 and 2200 ---")
    in_range = alltime_lb.get_players_in_score_range(1800, 2200)
    for entry in in_range:
        print(f" {entry['player']}: {entry['score']}")

    # ---------- Exercise 3: TTL on daily leaderboard ----------
    print("\n--- Exercise 3: Setting TTL of 7 days on daily leaderboard ---")
    daily_lb.set_daily_ttl(days=7)
    ttl = daily_lb.r.ttl(daily_lb.key)
    print(f" TTL set on '{daily_lb.key}': {ttl} seconds (~7 days = 604800 seconds)")


if __name__ == "__main__":
    demo()
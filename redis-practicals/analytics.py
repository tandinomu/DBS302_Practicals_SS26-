import redis
from typing import Optional, List


class RealtimeAnalytics:
    """
    Real-time analytics using Redis bitmaps and HyperLogLog.
    Tracks:
      - Daily Active Users (DAU) via bitmaps.
      - Daily Unique Visitors (UV) via HyperLogLog.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        self.r = redis_client or redis.Redis(
            host="127.0.0.1",
            port=6379,
            db=0,
            decode_responses=True,
        )

    # --------------------
    # Bitmap-based metrics
    # --------------------
    def _dau_key(self, date_str: str) -> str:
        """
        Build key for daily active user bitmap.
        Example date_str: '2026-03-17'.
        """
        return f"analytics:dau:{date_str}"

    def mark_user_active(self, date_str: str, user_id: int) -> None:
        """
        Mark a user as active for a given day using SETBIT.
        """
        if user_id < 0:
            raise ValueError("user_id must be non-negative")

        key = self._dau_key(date_str)
        # Set bit at position = user_id
        self.r.setbit(key, user_id, 1)

    def is_user_active(self, date_str: str, user_id: int) -> bool:
        """
        Check whether the user was active on a given day using GETBIT.
        """
        key = self._dau_key(date_str)
        bit_value = self.r.getbit(key, user_id)
        return bit_value == 1

    def count_daily_active_users(self, date_str: str) -> int:
        """
        Count daily active users for the given date using BITCOUNT.
        """
        key = self._dau_key(date_str)
        return self.r.bitcount(key)

    # ------------------------
    # HyperLogLog-based metrics
    # ------------------------
    def _uv_key(self, date_str: str) -> str:
        """
        Build key for daily unique visitors HyperLogLog.
        """
        return f"analytics:uv:{date_str}"

    def add_visit(self, date_str: str, user_identifier: str) -> None:
        """
        Add a visit for a given day in HyperLogLog.
        user_identifier can be a user_id, session_id, or IP string.
        """
        key = self._uv_key(date_str)
        self.r.pfadd(key, user_identifier)

    def count_unique_visitors(self, date_str: str) -> int:
        """
        Get approximate number of unique visitors for the given date using PFCOUNT.
        """
        key = self._uv_key(date_str)
        return self.r.pfcount(key)

    # ========== EXERCISE 1: MERGE UV ==========
    def merge_uv(self, target_date: str, source_dates: List[str]) -> None:
        """
        Exercise 1: Merge multiple daily HyperLogLogs into a weekly key using PFMERGE.
        """
        target_key = self._uv_key(target_date)
        source_keys = [self._uv_key(date) for date in source_dates]
        self.r.pfmerge(target_key, *source_keys)

    # ========== EXERCISE 2: STICKINESS RATIO ==========
    def get_stickiness_ratio(self, date_str: str, month_dates: List[str]) -> float:
        """
        Exercise 2: Compute stickiness ratio = DAU / MAU
        Returns ratio as percentage.
        """
        # Get DAU for the specific date
        dau = self.count_unique_visitors(date_str)
        
        # Create month key (e.g., analytics:uv:month:2026-03)
        month_key = f"analytics:uv:month:{date_str[:7]}"
        
        # Get all source keys for the month
        source_keys = [self._uv_key(d) for d in month_dates]
        
        # Delete previous month key if exists and merge all daily keys
        self.r.delete(month_key)
        self.r.pfmerge(month_key, *source_keys)
        
        # Get MAU (Monthly Active Users)
        mau = self.r.pfcount(month_key)
        
        # Calculate stickiness ratio
        if mau == 0:
            return 0.0
        
        ratio = (dau / mau) * 100
        return ratio


def demo():
    analytics = RealtimeAnalytics()

    date = "2026-03-17"

    # Clear previous demo data
    analytics.r.delete(analytics._dau_key(date))
    analytics.r.delete(analytics._uv_key(date))
    
    # Clear exercise data
    analytics.r.delete(analytics._uv_key("2026-03-15"))
    analytics.r.delete(analytics._uv_key("2026-03-16"))
    analytics.r.delete(analytics._uv_key("week-2026-03-15"))
    analytics.r.delete("analytics:uv:month:2026-03")

    # Simulate some activity
    print(f"Simulating activity for {date}...")

    # Users 1, 42, 100 are active
    analytics.mark_user_active(date, 1)
    analytics.mark_user_active(date, 42)
    analytics.mark_user_active(date, 100)

    # Visits (note repeated identifiers)
    analytics.add_visit(date, "user1")
    analytics.add_visit(date, "user2")
    analytics.add_visit(date, "user3")
    analytics.add_visit(date, "user2")  # duplicate
    analytics.add_visit(date, "user3")  # duplicate
    analytics.add_visit(date, "user4")

    # Check a user's activity
    print("\nIs user 42 active?")
    print(" ->", analytics.is_user_active(date, 42))

    # Daily active users (exact, from bitmap)
    dau = analytics.count_daily_active_users(date)
    print("\nDaily Active Users (DAU):", dau)

    # Unique visitors (approximate, from HyperLogLog)
    uv = analytics.count_unique_visitors(date)
    print("Unique Visitors (UV) [approx]:", uv)

    # ========== EXERCISE 1: MERGE UV ==========
    print("\n" + "="*50)
    print("EXERCISE 1: Weekly Unique Visitors (PFMERGE)")
    print("="*50)
    
    # Clear previous exercise data
    analytics.r.delete(analytics._uv_key("2026-03-15"))
    analytics.r.delete(analytics._uv_key("2026-03-16"))
    analytics.r.delete(analytics._uv_key("2026-03-17"))
    analytics.r.delete(analytics._uv_key("week-2026-03-15"))
    
    # Add data for multiple days
    analytics.add_visit("2026-03-15", "user1")
    analytics.add_visit("2026-03-15", "user2")
    analytics.add_visit("2026-03-15", "user3")
    
    analytics.add_visit("2026-03-16", "user2")
    analytics.add_visit("2026-03-16", "user3")
    analytics.add_visit("2026-03-16", "user4")
    analytics.add_visit("2026-03-16", "user5")
    
    analytics.add_visit("2026-03-17", "user3")
    analytics.add_visit("2026-03-17", "user4")
    analytics.add_visit("2026-03-17", "user5")
    analytics.add_visit("2026-03-17", "user6")
    
    # Show individual day counts
    print("\nIndividual Day Counts:")
    print(f"  March 15: {analytics.count_unique_visitors('2026-03-15')} unique visitors")
    print(f"  March 16: {analytics.count_unique_visitors('2026-03-16')} unique visitors")
    print(f"  March 17: {analytics.count_unique_visitors('2026-03-17')} unique visitors")
    
    # Merge into weekly key
    analytics.merge_uv("week-2026-03-15", ["2026-03-15", "2026-03-16", "2026-03-17"])
    weekly_uv = analytics.count_unique_visitors("week-2026-03-15")
    
    print(f"\nWeekly Unique Visitors (March 15-17): {weekly_uv}")
    print("(Should be 6 unique users: user1, user2, user3, user4, user5, user6)")

    # ========== EXERCISE 2: STICKINESS RATIO ==========
    print("\n" + "="*50)
    print("EXERCISE 2: Stickiness Ratio (DAU / MAU)")
    print("="*50)
    
    # Prepare March dates
    march_dates = ["2026-03-15", "2026-03-16", "2026-03-17"]
    
    # Add some more data for March to simulate a month
    analytics.add_visit("2026-03-14", "user1")
    analytics.add_visit("2026-03-14", "user7")
    analytics.add_visit("2026-03-13", "user8")
    analytics.add_visit("2026-03-12", "user9")
    
    # Extended dates for better MAU calculation
    extended_dates = ["2026-03-12", "2026-03-13", "2026-03-14", "2026-03-15", "2026-03-16", "2026-03-17"]
    
    # Add visits for these extended dates
    analytics.add_visit("2026-03-12", "user9")
    analytics.add_visit("2026-03-13", "user8")
    analytics.add_visit("2026-03-14", "user1")
    analytics.add_visit("2026-03-14", "user7")
    
    # Calculate stickiness for March 17
    ratio = analytics.get_stickiness_ratio("2026-03-17", extended_dates)
    
    dau = analytics.count_unique_visitors("2026-03-17")
    mau = analytics.r.pfcount("analytics:uv:month:2026-03")
    
    print(f"\nStickiness Analysis for March 17:")
    print(f"  Daily Active Users (DAU): {dau}")
    print(f"  Monthly Active Users (MAU): {mau}")
    print(f"  Stickiness Ratio: {ratio:.2f}%")
    print("\n  (Stickiness ratio shows how engaged users are -")
    print("   higher percentage means users visit frequently)")


if __name__ == "__main__":
    demo()
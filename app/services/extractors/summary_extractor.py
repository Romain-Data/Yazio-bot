import re
from datetime import date, datetime, timedelta
from typing import Optional

from app.models.analysis import RepasAnalysis
from app.services.extractors.base_extractor import BaseExtractor
from app.services.yazio_service import YazioService


class SummaryExtractor(BaseExtractor):
    def __init__(self, api_key: str, api_url: str, text_model_id: str, image_model_id: str, yazio_service: Optional[YazioService] = None):
        super().__init__(api_key, api_url, text_model_id, image_model_id)
        self.yazio_service = yazio_service or YazioService()

    def analyze_text(self, text: str, local_time: str) -> RepasAnalysis:
        cleaned = text.strip().lower() if text else ""
        today = date.today()

        if "hier" in cleaned or "yesterday" in cleaned:
            target_date = today - timedelta(days=1)
            daily = self.yazio_service.get_daily_summary(target_date.strftime("%Y-%m-%d"))
            formatted = self.yazio_service.format_daily_summary(daily)
            return RepasAnalysis(
                repas="snack",
                aliments=[],
                total_kcal=float(daily["kcal"]),
                total_proteines=float(daily["protein"]),
                total_glucides=float(daily["carb"]),
                total_lipides=float(daily["fat"]),
                is_summary=True,
                summary_text=formatted
            )

        if "aujourd'hui" in cleaned or "today" in cleaned or "jour" in cleaned and "semaine" not in cleaned and "7" not in cleaned:
            target_date = today
            daily = self.yazio_service.get_daily_summary(target_date.strftime("%Y-%m-%d"))
            formatted = self.yazio_service.format_daily_summary(daily)
            return RepasAnalysis(
                repas="snack",
                aliments=[],
                total_kcal=float(daily["kcal"]),
                total_proteines=float(daily["protein"]),
                total_glucides=float(daily["carb"]),
                total_lipides=float(daily["fat"]),
                is_summary=True,
                summary_text=formatted
            )

        if "7j" in cleaned or "7 j" in cleaned or "7 jours" in cleaned or "glissant" in cleaned:
            weekly = self.yazio_service.get_weekly_summary(rolling_7d=True)
            formatted = self.yazio_service.format_weekly_summary(weekly)
            return RepasAnalysis(
                repas="snack",
                aliments=[],
                total_kcal=float(weekly["total_kcal"]),
                total_proteines=float(weekly["total_protein"]),
                total_glucides=float(weekly["total_carb"]),
                total_lipides=float(weekly["total_fat"]),
                is_summary=True,
                summary_text=formatted
            )

        if "derniere" in cleaned or "dernière" in cleaned or "passée" in cleaned or "passee" in cleaned or "last" in cleaned:
            start_last_week = today - timedelta(days=today.weekday() + 7)
            end_last_week = start_last_week + timedelta(days=6)
            weekly = self.yazio_service.get_weekly_summary(start_date=start_last_week, end_date=end_last_week)
            formatted = self.yazio_service.format_weekly_summary(weekly)
            return RepasAnalysis(
                repas="snack",
                aliments=[],
                total_kcal=float(weekly["total_kcal"]),
                total_proteines=float(weekly["total_protein"]),
                total_glucides=float(weekly["total_carb"]),
                total_lipides=float(weekly["total_fat"]),
                is_summary=True,
                summary_text=formatted
            )

        # Default: Current week from Monday to today
        weekly = self.yazio_service.get_weekly_summary()
        formatted = self.yazio_service.format_weekly_summary(weekly)
        return RepasAnalysis(
            repas="snack",
            aliments=[],
            total_kcal=float(weekly["total_kcal"]),
            total_proteines=float(weekly["total_protein"]),
            total_glucides=float(weekly["total_carb"]),
            total_lipides=float(weekly["total_fat"]),
            is_summary=True,
            summary_text=formatted
        )

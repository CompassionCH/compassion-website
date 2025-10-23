##############################################################################
#
#    Copyright (C) 2020 Compassion CH (http://www.compassion.ch)
#    @author: Théo Nikles <theo.nikles@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import logging

from odoo import fields, models, tools

logger = logging.getLogger(__name__)

try:
    from pytz import timezone
except (OSError, ImportError):
    logger.warning("Please install pytz")


class CompassionProject(models.Model):
    _inherit = "compassion.project"

    supported_types = ["cognitive", "physical", "socio", "spiritual"]

    center_current_time = fields.Datetime(
        string="Current Time", compute="_compute_current_time"
    )
    weather_icon_id = fields.Char(
        string="Current Weather Icon Id", compute="_compute_weather_icon_id"
    )
    current_temperature_celsius = fields.Float(
        string="Current Temperature (°C)",
        compute="_compute_current_temperature",
        store=False,
    )

    def get_activity_for_age(self, age, activity_type="physical"):
        if activity_type and activity_type not in self.supported_types:
            raise ValueError(
                f"Type {activity_type} is not supported."
                f"It should be in {self.supported_types}"
            )
        if age < 0:
            raise ValueError("Age needs to be positive")
        elif age <= 5:
            return getattr(self, f"{activity_type}_activity_babies_ids")
        elif age <= 11:
            return getattr(self, f"{activity_type}_activity_kids_ids")
        else:
            return getattr(self, f"{activity_type}_activity_ados_ids")

    def _compute_current_time(self):
        """
        Computes the current time.
        Odoo automatically handles timezone conversion for display.
        The value should be assigned in UTC.
        """
        now_utc = fields.Datetime.now()
        for record in self:
            tzinfo = timezone(record.timezone) if record.timezone else tools.utc
            record.center_current_time = now_utc.astimezone(tzinfo).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

    def _compute_current_temperature(self):
        """
        Computes the current temperature in celsius.
        """
        for record in self:
            record.update_weather()
            if record.current_temperature:
                # Convert from Kelvin to Celsius
                KELVIN_TO_CELSIUS_OFFSET = 273.15
                record.current_temperature_celsius = round(
                    record.current_temperature - KELVIN_TO_CELSIUS_OFFSET, 1
                )

            else:
                record.current_temperature_celsius = False

    def _compute_weather_icon_id(self):
        """
        Computes the current weather icon.
        """
        for record in self:
            record.update_weather()
            current_hour = record.center_current_time.hour
            DAY_STARTS_HOUR = 6
            DAY_ENDS_HOUR = 19
            is_day = DAY_STARTS_HOUR <= current_hour < DAY_ENDS_HOUR

            icon_id = ""
            # Generate the icon id in the kebab-case format
            weather = record.current_weather
            if weather == "Clear":
                icon_id = "sun" if is_day else "moon-star"
            elif weather == "Clouds":
                icon_id = "cloud-blank02"
            elif weather in ("Rain", "Storm"):
                icon_id = "cloud-raining04"
            elif weather in (
                "Mist",
                "Haze",
                "Fog",
                "Smoke",
                "Dust",
                "Sand",
                "Drizzle",
                "Ash",
            ):
                icon_id = "waves"
            elif weather == "Thunderstorm":
                icon_id = "cloud-lightning"
            elif weather == "Snow":
                icon_id = "snowflake01"
            elif weather in ("Tornado", "Squall"):
                icon_id = "wind03"
            else:
                icon_id = "sun" if is_day else "moon-star"

            record.weather_icon_id = icon_id

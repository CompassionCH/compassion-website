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
            if record.current_temperature:
                record.update_weather()
                # Convert from Kelvin to Celsius
                record.current_temperature_celsius = round(
                    record.current_temperature - 273.15, 1
                )

    def _compute_weather_icon_id(self):
        """
        Computes the current weather icon.
        """
        for record in self:
            self.ensure_one()
            record.update_weather()
            current_hour = record.center_current_time.hour
            isDay = 6 <= current_hour < 19

            icon_id = ""

            match record.current_weather:
                case "Clear":
                    icon_id = "Sun" if isDay else "MoonStar"
                case "Clouds":
                    icon_id = "CloudBlank02"
                case "Rain" | "Storm":
                    icon_id = "CloudRaining04"
                case (
                    "Mist"
                    | "Haze"
                    | "Fog"
                    | "Smoke"
                    | "Dust"
                    | "Sand"
                    | "Drizzle"
                    | "Ash"
                ):
                    icon_id = "Waves"
                case "Thunderstorm":
                    icon_id = "CloudLightning"
                case "Snow":
                    icon_id = "Snowflake01"
                case "Tornado" | "Squall":
                    icon_id = "Wind03"
                case _:
                    icon_id = "Sun" if isDay else "Moon01"

            record.weather_icon_id = f"{icon_id}.svg"

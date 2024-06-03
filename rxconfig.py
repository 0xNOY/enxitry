import reflex as rx

from enxitry.config import CONFIG

config = rx.Config(
    app_name="enxitry",
    timeout=CONFIG.reflex_timeout,
)

import reflex as rx

from enxitry.config import CONFIG

config = rx.Config(
    app_name="enxitry",
    db_url="shillelagh://",
    adapter_kwargs={
        "gsheetsapi": {
            "service_account_file": str(CONFIG.gsheets_service_account_file),
            "catalog": {
                "students": "https://docs.google.com/spreadsheets/d/13Ai5BKBOW1XVWt6UIFqfaKEdxiSo1Zy67xg8J7Zs3HQ/edit?headers=1#gid=113374742",
                "log": "https://docs.google.com/spreadsheets/d/13Ai5BKBOW1XVWt6UIFqfaKEdxiSo1Zy67xg8J7Zs3HQ/edit?headers=1#gid=2101805944",
            },
        }
    },
)

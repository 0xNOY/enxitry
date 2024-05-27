from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)


class Config(BaseSettings):
    data_dir: Path = Path("~/.enxitry").expanduser()
    config_path: Path = data_dir / "config.toml"

    timezone: str = "Asia/Tokyo"

    gsheets_service_account_file: Path = data_dir / "gsheets-cred.json"
    gsheets_url: str = ""

    nfc_device_index: int = 0
    nfc_reading_interval: float = 0.1

    ocr_camera_index: int = 0
    ocr_camera_rotation: int = 0
    ocr_timeout: int = 30
    ocr_info_valid_timeout: int = 8

    registration_completion_display_time: int = 5

    students_table_update_interval: float = 15

    model_config = SettingsConfigDict(
        env_prefix="ENXITRY_",
        toml_file=config_path,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: BaseSettings,
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            TomlConfigSettingsSource(settings_cls),
            dotenv_settings,
            env_settings,
        )


CONFIG = Config()

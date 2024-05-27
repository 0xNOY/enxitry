import datetime
from enum import StrEnum
from typing import Self, Callable

from cuid2 import cuid_wrapper
from pydantic import BaseModel
import pytz

from enxitry.config import CONFIG
from .gspread import GSpreadTable


cuid2 = cuid_wrapper()


class LogAction(StrEnum):
    """
    ログのアクションを表す列挙型
    """

    ENTER = "enter"
    EXIT = "exit"
    REGISTER = "register"
    UNREGISTER = "unregister"


class Log(BaseModel):
    """
    ログを表すモデル

    Attributes:
        id (str): ログID
        student_id (str): 学籍番号
        timestamp (int): タイムスタンプ
        action (LogAction): アクション
    """

    id: str
    student_id: str
    timestamp: datetime.datetime
    action: LogAction

    @classmethod
    def create(cls, student_id: str, action: LogAction) -> Self:
        """
        ログを生成する

        Args:
            student_id (str): 学籍番号
            action (LogAction): アクション

        Returns:
            Log: 生成されたログ
        """
        return cls(
            id=cuid2(),
            student_id=student_id,
            timestamp=datetime.datetime.now(tz=pytz.timezone(CONFIG.timezone)),
            action=action,
        )


class DefaultLogTable(GSpreadTable[Log]):
    """ログのデータベース。シングルトン。"""

    def __new__(cls, *args, **kargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            super().__init__(
                cls._instance,
                Log,
                CONFIG.gsheets_url,
                CONFIG.gsheets_service_account_file,
            )
        return cls._instance

    def __init__(self):
        pass

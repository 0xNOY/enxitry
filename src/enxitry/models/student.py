from enum import StrEnum

from pydantic import BaseModel

from enxitry.config import CONFIG
from .gspread import GSpreadTable


class StudentStatus(StrEnum):
    """
    在室状態を表す列挙型
    """

    ENTERED = "entered"
    EXITED = "exited"


class Student(BaseModel):
    """
    学生を表すモデル

    Attributes:
        sid (str): 学籍番号
        idm (str): 学生証のIDm
        name (str): 学生氏名
        status (StudentStatus): 在室状態
    """

    sid: str
    idm: str
    name: str
    status: StudentStatus


class DefaultStudentsTable(GSpreadTable[Student]):
    """学生のデータベース。シングルトン。"""

    def __new__(cls, *args, **kargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            super().__init__(
                cls._instance,
                Student,
                CONFIG.gsheets_url,
                CONFIG.gsheets_service_account_file,
            )
        return cls._instance

    def __init__(self):
        pass

    def get_by_idm(self, idm: str) -> Student | None:
        """
        IDmから学生を取得する

        Args:
            idm (str): IDm

        Returns:
            Student | None: 学生。見つからなかった場合はNone。
        """
        for student in self.get_all():
            if student.idm == idm:
                return student
        return None

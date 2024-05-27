from dataclasses import asdict
from pathlib import Path

import pandas as pd
from pydantic import BaseModel
from gspread_pandas import Spread
from gspread_pandas.conf import get_config


class GSpreadTable[T]:
    """Google Sheetsをデータベースとして利用するためのクラス"""

    def __init__(
        self,
        model: T,
        spreads_url: str,
        service_account_file: Path,
        sheet_name: str = "",
        index_col: str = "",
    ):
        """
        Args:
            model (T): モデルとなるデータクラス。pydantic.BaseModelを継承している必要がある。
            spreads_url (str): スプレッドシートのURL
            service_account_file (Path): サービスアカウントファイル
            sheet_name (str): シート名。空文字列の場合はモデル名が利用される。
            index_col (str): インデックスとするフィールド名。空文字列の場合はモデルの最初に定義されたフィールドが利用される。
        """

        if sheet_name == "":
            sheet_name = model.__name__

        if index_col == "":
            index_col = list(model.model_fields)[0]

        self._index_col = index_col
        self._model = model

        conf = get_config(service_account_file.parent, service_account_file.name)
        self._spread = Spread(
            spreads_url,
            sheet=sheet_name,
            config=conf,
            create_sheet=True,
        )

    def _model_df(self) -> pd.DataFrame:
        """
        モデルのデータフレームを取得する。

        Returns:
            pd.DataFrame: モデルのデータフレーム
        """
        columns = list(self._model.model_fields)
        df = pd.DataFrame(columns=columns)
        df.set_index(self._index_col, inplace=True)
        return df

    def get_all_as_df(self) -> pd.DataFrame:
        """
        データベースの内容をDataFrameとして全て取得する。

        Returns:
            pd.DataFrame: データベースの内容
        """

        df = self._spread.sheet_to_df()
        if df.empty:
            df = self._model_df()
        return df

    def get_all(self) -> list[T]:
        """
        データベースの内容を全て取得する。

        Returns:
            list[T]: データベースの内容
        """
        df = self.get_all_as_df()
        if df.empty:
            return []
        df.reset_index(inplace=True)
        df = df.apply(lambda x: self._model(**x), axis=1)
        return list(df)

    def get_by_index(self, index: str) -> T | None:
        """
        indexに対応するデータを取得する。

        Args:
            index (str): インデックス

        Returns:
            T | None: インデックスに対応するデータベースの内容。見つからない場合は None。
        """
        df = self.get_all_as_df()
        row = df[df[self._index_col] == index]
        if row.empty:
            return None
        return self._model(**row)

    def update(self, rows: list[T]):
        """
        データベースの内容を更新する。データのインデックスが存在しない場合は新規追加する。

        Args:
            rows (T | list[T]): 更新するデータ
        """
        df = self.get_all_as_df()
        for row in rows:
            row_dict = row.model_dump()
            index = row.__getattribute__(self._index_col)
            df.loc[index] = row_dict
        self._spread.df_to_sheet(df)

    def delete(self, indexes: list[str]):
        """
        インデックスに対応するデータを削除する。

        Args:
            indexes (list[str]): 削除するデータのインデックス
        """
        df = self.get_all_as_df()
        df.drop(indexes, inplace=True)
        self._spread.df_to_sheet(df, replace=True)

from dataclasses import dataclass
from time import time
from typing import Literal

import cv2
import numpy as np
from paddleocr_onnx import PaddleOcrONNX, get_paddleocr_parameter
from paddleocr_onnx.pocr_onnx import PPOCR_DIR

from enxitry.config import CONFIG


@dataclass
class InfoWrittenOnCard:
    """
    学生証に明記されている情報を表すデータクラス

    Attributes:
        student_id (str): 学籍番号
        student_name (str): 学生氏名
    """

    student_id: str
    student_name: str


class CardOCR:
    """
    学生証に書かれた情報を読み取るOCRクラス

    Attributes:
        camera_rotation (Literal[0, 90, 180, 270]): カメラの回転角度
        last_frame (np.ndarray | None): 最後に読み取ったフレーム
    """

    def __init__(
        self,
        camera_index: int = CONFIG.ocr_camera_index,
    ):
        """
        Args:
            camera_index (int): カメラのインデックス
        """
        param = get_paddleocr_parameter()
        param.rec_model_dir = PPOCR_DIR / "model/rec_model/en_PP-OCRv3_rec_infer.onnx"
        param.rec_image_shape = "3, 48, 320"
        self._ocr = PaddleOcrONNX(param)

        self._camera = cv2.VideoCapture(camera_index)

        self.camera_rotation: Literal[0, 90, 180, 270] = CONFIG.ocr_camera_rotation
        self.last_frame: np.ndarray | None = None

    def __del__(self):
        self._camera.release()

    def find_card_info(self) -> InfoWrittenOnCard | None:
        """
        学生証に書かれた情報を読み取る

        Returns:
            InfoWrittenOnCard | None: 読み取った情報。読み取れなかった場合はNone。
        """
        ret, frame = self._camera.read()
        if not ret or frame is None:
            return None

        self.last_frame = frame

        if self.camera_rotation != 0:
            frame = cv2.rotate(frame, self.camera_rotation)

        bboxes, texts, time = self._ocr(frame)

        sid = None
        for box, (text, score) in zip(bboxes, texts):
            if sid is None:
                if text.isdigit() and len(text) == 9:
                    sid = text
            else:
                if "," in text:  # カンマを含む文字列を氏名として扱う
                    return InfoWrittenOnCard(sid, text)

        return None

    def find_card_info_with_timeout(
        self, timeout_sec: float = 0
    ) -> InfoWrittenOnCard | None:
        """
        学生証に書かれた情報を読み取る

        Args:
            timeout_sec (float): 読み取りを試みる最大時間（秒）。0以下の場合は1回だけ試みる。

        Returns:
            InfoWrittenOnCard | None: 読み取った情報。読み取れなかった場合はNone。
        """

        if timeout_sec <= 0:
            return self.find_card_info()

        start_time = time()
        while time() - start_time < timeout_sec:
            info = self.find_card_info()
            if info is not None:
                return info

        return None

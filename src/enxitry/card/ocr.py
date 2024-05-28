from dataclasses import dataclass
from time import time
from typing import Literal

import cv2
import numpy as np
from paddleocr_onnx import PaddleOcrONNX, get_paddleocr_parameter
from paddleocr_onnx.pocr_onnx import PPOCR_DIR

from enxitry.config import CONFIG


_default_ocr: PaddleOcrONNX | None = None
_default_camera: cv2.VideoCapture | None = None


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


def get_default_ocr() -> PaddleOcrONNX:
    """
    デフォルトのOCRインスタンスを取得する

    Returns:
        PaddleOcrONNX: OCRインスタンス
    """
    global _default_ocr
    if _default_ocr is None:
        param = get_paddleocr_parameter()
        param.rec_model_dir = PPOCR_DIR / "model/rec_model/en_PP-OCRv3_rec_infer.onnx"
        param.rec_image_shape = "3, 48, 320"
        _default_ocr = PaddleOcrONNX(param)
    return _default_ocr


def unload_default_ocr():
    """
    デフォルトのOCRインスタンスを解放する
    """
    global _default_ocr
    _default_ocr = None


def get_default_camera() -> cv2.VideoCapture:
    """
    デフォルトのカメラインスタンスを取得する

    Returns:
        cv2.VideoCapture: カメラインスタンス
    """
    global _default_camera
    if _default_camera is None or not _default_camera.isOpened():
        _default_camera = cv2.VideoCapture(CONFIG.ocr_camera_index)
    return _default_camera


def unload_default_camera():
    """
    デフォルトのカメラインスタンスを解放する
    """
    global _default_camera
    if _default_camera is not None:
        _default_camera.release()
    _default_camera = None


def find_card_info(img: cv2.Mat) -> InfoWrittenOnCard | None:
    """
    学生証に書かれた情報を読み取る

    Args:
        img (cv2.Mat): 画像

    Returns:
        InfoWrittenOnCard | None: 読み取った情報。読み取れなかった場合はNone。
    """
    ocr = get_default_ocr()
    bboxes, texts, time = ocr(img)

    sid = None
    for box, (text, score) in zip(bboxes, texts):
        if sid is None:
            if text.isdigit() and len(text) == 9:
                sid = text
        else:
            if "," in text:  # カンマを含む文字列を氏名として扱う
                return InfoWrittenOnCard(sid, text)

    return None

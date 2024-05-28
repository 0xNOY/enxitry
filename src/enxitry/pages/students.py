from asyncio import sleep, create_task
from enum import Enum
import time
from threading import Thread

import PIL.Image
import reflex as rx
import pandas as pd
import PIL
import cv2
import reflex.components as rxc
from loguru import logger


from enxitry.config import CONFIG
from enxitry.models import (
    DefaultLogTable,
    DefaultStudentsTable,
    Student,
    StudentStatus,
    Log,
    LogAction,
)
from enxitry.card import FelicaReader, ocr


nfc_reader = FelicaReader()
background_session_id = 0


class NFCStatus(Enum):
    BUSY = ("BUSY", "red")
    READY = ("READY", "green")


class State(rx.State):
    students: pd.DataFrame

    nfc_status_text: str = NFCStatus.BUSY.value[0]
    nfc_status_color: str = NFCStatus.BUSY.value[1]

    is_open_register_dialog_1: bool = False
    is_open_register_dialog_2: bool = False
    is_open_register_dialog_3: bool = False
    camera_image: PIL.Image.Image | None
    recognized_info: list[list[str]]
    ocr_info_valid_time_prog: int = 0

    def _update_table(self):
        df = DefaultStudentsTable().get_all_as_df()
        df = df[df["status"] == StudentStatus.ENTERED]
        df.drop(["idm", "status"], axis=1, inplace=True)
        df.columns = ["氏名"]
        return df

    def set_nfc_status(self, status: NFCStatus):
        self.nfc_status_text = status.value[0]
        self.nfc_status_color = status.value[1]

    @rx.background
    async def watch_table(self):
        global background_session_id

        watcher_cls = background_session_id

        while watcher_cls == background_session_id:
            df = self._update_table()
            async with self:
                self.students = df

            await sleep(CONFIG.students_table_update_interval)

    async def get_idm(self, timeout=0, should_update_nfc_status=True) -> str:
        global nfc_reader

        if should_update_nfc_status:
            async with self:
                self.set_nfc_status(NFCStatus.READY)

        idm = None
        if timeout <= 0:
            idm = nfc_reader.get_idm()
        else:
            start_time = time.time()
            while idm is None and time.time() - start_time < timeout:
                idm = nfc_reader.get_idm()
                await sleep(CONFIG.nfc_reading_interval)

        if should_update_nfc_status:
            async with self:
                self.set_nfc_status(NFCStatus.BUSY)

        return idm

    async def register_student(self, idm: str):
        async with self:
            self.is_open_register_dialog_1 = True

        camera = ocr.get_default_camera()
        cam_fps = camera.get(cv2.CAP_PROP_FPS)

        start_time = time.time()
        while time.time() - start_time < CONFIG.delay_before_ocr:
            ret, frame = camera.read()
            if not ret or frame is None:
                continue
            factor = min(1, CONFIG.size_displayed_camera_image / max(frame.shape[:2]))
            frame = PIL.Image.fromarray(
                cv2.cvtColor(
                    cv2.resize(frame, (0, 0), fx=factor, fy=factor), cv2.COLOR_BGR2RGB
                )
            )
            async with self:
                self.camera_image = frame
            await sleep(1 / cam_fps)

        start_time = time.time()
        ocr_thread = None
        while time.time() - start_time < CONFIG.ocr_timeout:
            ret, frame = camera.read()
            if not ret or frame is None:
                continue

            if ocr_thread is not None and not ocr_thread.is_alive():
                ocr_thread.join()
                info = ocr_thread.result
                if info:
                    break
                ocr_thread = None

            if ocr_thread is None:
                ocr_thread = Thread(
                    target=lambda: setattr(
                        ocr_thread, "result", ocr.find_card_info(frame)
                    )
                )
                ocr_thread.start()

            factor = min(1, CONFIG.size_displayed_camera_image / max(frame.shape[:2]))
            frame = PIL.Image.fromarray(
                cv2.cvtColor(
                    cv2.resize(frame, (0, 0), fx=factor, fy=factor), cv2.COLOR_BGR2RGB
                )
            )
            async with self:
                self.camera_image = frame
            await sleep(1 / cam_fps)

        async with self:
            self.is_open_register_dialog_1 = False
            self.camera_image = None

        ocr.unload_default_camera()

        if not info:
            return

        async with self:
            self.recognized_info = [[info.student_id, info.student_name]]
            self.is_open_register_dialog_2 = True

        task_get_idm = create_task(self.get_idm(timeout=CONFIG.ocr_info_valid_timeout))

        async with self:
            self.ocr_info_valid_time_prog = 0

        for i in range(CONFIG.ocr_info_valid_timeout):
            if task_get_idm.done():
                break
            await sleep(1)
            async with self:
                self.ocr_info_valid_time_prog = i

        async with self:
            self.is_open_register_dialog_2 = False

        _idm = await task_get_idm
        if idm != _idm:
            return await self.register_student(idm)

        async with self:
            self.is_open_register_dialog_3 = True

        start_time = time.time()

        student = Student(
            sid=info.student_id,
            idm=idm,
            name=info.student_name,
            status=StudentStatus.ENTERED,
        )

        DefaultStudentsTable().update([student])
        DefaultLogTable().update(
            [
                Log.create(student.sid, LogAction.REGISTER),
                Log.create(student.sid, LogAction.ENTER),
            ]
        )

        df = self._update_table()
        async with self:
            self.students = df

        delay = CONFIG.registration_completion_display_time - (time.time() - start_time)
        if delay > 0:
            await sleep(delay)

        async with self:
            self.is_open_register_dialog_3 = False

    @rx.background
    async def watch_nfc(self):
        global background_session_id

        watcher_cls = background_session_id

        async with self:
            self.set_nfc_status(NFCStatus.READY)

        while watcher_cls == background_session_id:
            idm = await self.get_idm(1, False)
            if idm is None:
                continue

            async with self:
                self.set_nfc_status(NFCStatus.BUSY)

            student = DefaultStudentsTable().get_by_idm(idm)
            if not student:
                try:
                    await self.register_student(idm)
                except Exception as e:
                    logger.error(f"Failed to register student: {e}")
                    yield rxc.toast.error(
                        "学生の登録に失敗しました。もう一度試してください。",
                    )
                async with self:
                    self.set_nfc_status(NFCStatus.READY)
                continue

            if student.status == StudentStatus.ENTERED:
                action = LogAction.EXIT
                student.status = StudentStatus.EXITED

                df = self.students
                df.drop(student.sid, inplace=True)

                yield rxc.toast.info(
                    f"{student.name}さん、お疲れ様です!",
                )
                async with self:
                    self.students = df
            else:
                action = LogAction.ENTER
                student.status = StudentStatus.ENTERED

                df = self.students
                df.at[student.sid, "氏名"] = student.name

                yield rxc.toast.success(
                    f"{student.name}さん、こんにちは!",
                )

                async with self:
                    self.last_action_sname = student.name
                    self.is_open_exit_greeting_toast = True
                    self.students = df

            DefaultStudentsTable().update([student])
            DefaultLogTable().update([Log.create(student.sid, action)])

            async with self:
                self.set_nfc_status(NFCStatus.READY)

    def increment_background_session_id(self):
        global background_session_id
        background_session_id += 1


@rx.page(
    on_load=[State.increment_background_session_id, State.watch_table, State.watch_nfc],
    route="/",
)
def members() -> rx.Component:
    return rx.container(
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("初めまして!"),
                rx.dialog.description(
                    "まずはカメラに学生証をかざして、学籍番号と氏名を教えてください。",
                    size="5",
                ),
                rx.center(
                    rx.image(src=State.camera_image, alt="カメラ画像"),
                ),
            ),
            open=State.is_open_register_dialog_1,
        ),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("読み取りに成功しました!"),
                rx.dialog.description(
                    "以下の",
                    rx.text.strong("情報が正しければ"),
                    f"、{CONFIG.ocr_info_valid_timeout}秒以内にNFCリーダに学生証をかざしてください。",
                    size="5",
                ),
                rx.data_table(data=State.recognized_info, columns=["学籍番号", "氏名"]),
                rx.progress(
                    value=CONFIG.ocr_info_valid_timeout
                    - State.ocr_info_valid_time_prog,
                    max=CONFIG.ocr_info_valid_timeout,
                ),
            ),
            open=State.is_open_register_dialog_2,
        ),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("登録が完了しました!"),
                rx.dialog.description(
                    "現在あなたの状態は在室になっています。退出時はNFCリーダに学生証をかざしてください。",
                    size="5",
                ),
            ),
            open=State.is_open_register_dialog_3,
        ),
        rx.vstack(
            rx.flex(
                rx.heading("在室管理システム (ベータ)", size="7"),
                rx.badge(
                    rx.flex(
                        rx.text("カードリーダー"),
                        rx.badge(
                            State.nfc_status_text,
                            color_scheme=State.nfc_status_color,
                        ),
                        align="center",
                        spacing="2",
                    ),
                    color_scheme="gray",
                    size="3",
                ),
                align="baseline",
                justify="between",
                direction="row",
                spacing="9",
            ),
            rx.text(
                "授業外でロボラボを利用する際は、入退出時にカードリーダへ学生証をかざしてください。",
                size="5",
            ),
            rx.heading("在室者一覧", size="6"),
            rx.data_table(
                data=State.students,
            ),
        ),
    )

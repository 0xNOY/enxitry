from smartcard.System import readers as get_readers
from smartcard.Exceptions import NoCardException
from smartcard.util import toHexString
from loguru import logger

from enxitry.config import CONFIG


class FelicaReader:
    """
    Felicaカードを読み取るクラス
    """

    def __init__(self):
        self._reader = get_readers()[CONFIG.nfc_device_index]

    def get_idm(self) -> str | None:
        """
        FelicaのカードIDmを取得する

        Returns:
            str | None: カードIDm。カードが読み取れなかった場合はNone。
        """
        connection = self._reader.createConnection()
        try:
            connection.connect()
        except NoCardException:
            return None
        except Exception as e:
            logger.error(f"Failed to connect to NFC: {e}")
            return None

        command = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        data, sw1, sw2 = connection.transmit(command)
        connection.disconnect()

        if sw1 == 0x90 and sw2 == 0x00 and len(data) == 8:
            return toHexString(data)

        logger.error(f"NFC APDU Failed. SW1: {sw1}, SW2: {sw2}")

        return None

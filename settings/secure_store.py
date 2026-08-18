import base64
import ctypes
from ctypes import wintypes
import logging

logger = logging.getLogger(__name__)

# Windows DPAPI structures & functions
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]

try:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    _CryptProtectData = crypt32.CryptProtectData
    _CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),  # pDataIn
        wintypes.LPCWSTR,           # szDataDescr
        ctypes.POINTER(DATA_BLOB),  # pOptionalEntropy
        ctypes.c_void_p,            # pvReserved
        ctypes.c_void_p,            # pPromptStruct
        wintypes.DWORD,             # dwFlags (0 or CRYPTPROTECT_UI_FORBIDDEN = 0x1)
        ctypes.POINTER(DATA_BLOB),  # pDataOut
    ]
    _CryptProtectData.restype = wintypes.BOOL

    _CryptUnprotectData = crypt32.CryptUnprotectData
    _CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),  # pDataIn
        ctypes.POINTER(wintypes.LPWSTR), # ppszDataDescr
        ctypes.POINTER(DATA_BLOB),  # pOptionalEntropy
        ctypes.c_void_p,            # pvReserved
        ctypes.c_void_p,            # pPromptStruct
        wintypes.DWORD,             # dwFlags
        ctypes.POINTER(DATA_BLOB),  # pDataOut
    ]
    _CryptUnprotectData.restype = wintypes.BOOL

    _LocalFree = kernel32.LocalFree
    _LocalFree.argtypes = [wintypes.HLOCAL]
    _LocalFree.restype = wintypes.HLOCAL

    DPAPI_AVAILABLE = True
except Exception as e:
    logger.warning("Windows DPAPI initialization failed: %s", e)
    DPAPI_AVAILABLE = False


def encrypt_string(plain_text: str) -> str:
    """
    Encrypts a plaintext string using Windows DPAPI (CryptProtectData)
    and returns a base64-encoded encrypted string.
    """
    if not plain_text:
        return ""
    
    if not DPAPI_AVAILABLE:
        # Fallback if DPAPI not available
        return base64.b64encode(plain_text.encode("utf-8")).decode("ascii")

    try:
        data_bytes = plain_text.encode("utf-8")
        blob_in = DATA_BLOB()
        blob_in.cbData = len(data_bytes)
        blob_in.pbData = ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte))

        blob_out = DATA_BLOB()
        # CRYPTPROTECT_UI_FORBIDDEN = 0x1
        success = _CryptProtectData(
            ctypes.byref(blob_in),
            "ScreenshotterSecret",
            None,
            None,
            None,
            0x1,
            ctypes.byref(blob_out),
        )

        if not success:
            raise ctypes.WinError()

        encrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        _LocalFree(blob_out.pbData)
        return base64.b64encode(encrypted_bytes).decode("ascii")
    except Exception as e:
        logger.error("Failed to encrypt with DPAPI: %s", e)
        # Fallback to base64 encoding to prevent crash
        return base64.b64encode(plain_text.encode("utf-8")).decode("ascii")


def decrypt_string(encrypted_b64: str) -> str:
    """
    Decrypts a base64-encoded ciphertext string using Windows DPAPI (CryptUnprotectData)
    and returns the original plaintext.
    """
    if not encrypted_b64:
        return ""

    try:
        encrypted_bytes = base64.b64decode(encrypted_b64)
    except Exception:
        return ""

    if not DPAPI_AVAILABLE:
        try:
            return encrypted_bytes.decode("utf-8")
        except Exception:
            return ""

    try:
        blob_in = DATA_BLOB()
        blob_in.cbData = len(encrypted_bytes)
        blob_in.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte))

        blob_out = DATA_BLOB()
        success = _CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            0x1,
            ctypes.byref(blob_out),
        )

        if not success:
            # Maybe it was stored as raw base64 plaintext fallback
            return encrypted_bytes.decode("utf-8")

        decrypted_bytes = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        _LocalFree(blob_out.pbData)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.debug("DPAPI decryption attempt fallback: %s", e)
        try:
            return encrypted_bytes.decode("utf-8")
        except Exception:
            return ""

from .custom_logger import CustomLogger

_LOGGER_INSTANCE = CustomLogger()
GLOBAL_LOGGER = _LOGGER_INSTANCE.get_logger()
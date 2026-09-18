import logging

from dunetrg.data.utils import temporary_log_level


class TestTemporaryLogLevel:
    def test_level_restored_after_context(self):
        logger = logging.getLogger("test_tmp_level")
        logger.setLevel(logging.WARNING)
        with temporary_log_level(logger, logging.DEBUG):
            inside = logger.level
        outside = logger.level
        print(f"\nlevel inside context: {inside} (DEBUG={logging.DEBUG}), "
              f"level after: {outside} (WARNING={logging.WARNING})")
        assert outside == logging.WARNING

    def test_level_changed_inside_context(self):
        logger = logging.getLogger("test_tmp_level_inside")
        logger.setLevel(logging.ERROR)
        with temporary_log_level(logger, logging.INFO):
            inside = logger.level
            print(f"\nlevel inside context: {inside} (INFO={logging.INFO})")
            assert inside == logging.INFO

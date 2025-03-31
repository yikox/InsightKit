from insight_kit import at_record,AT
import time

@at_record
def test2():
    time.sleep(0.1)
    AT.begin_record("test2-1")
    time.sleep(0.1)
    AT.end_record("test2-1")


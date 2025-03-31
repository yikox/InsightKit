import time
from insight_kit import AT
from test2 import test2
if __name__ == "__main__":
    AT.reset("atimer_test")
    AT.begin_record("Main")
    time.sleep(0.1)
    AT.begin_record("Sub1")
    time.sleep(0.1)
    AT.end_record("Sub1")
    for i in range(10):
        test2()
    AT.end_record("Main")
    AT.begin_record("Main1-xxxxxxxx")
    time.sleep(0.1)
    AT.end_record("Main1-xxxxxxxx")

    # AT.save()

    print(AT)
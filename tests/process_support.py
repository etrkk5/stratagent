"""Portable bounded child readiness; Windows select() cannot read pipe handles."""
import queue
import threading


def wait_ready(testcase, process, timeout=15):
    lines = queue.Queue()
    reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        line = lines.get(timeout=timeout)
    except queue.Empty:
        testcase.fail("Worker did not reach its durable checkpoint before the timeout.")
    testcase.assertEqual(line.strip(), "ready", process.stderr.read() if process.poll() is not None else "Worker checkpoint failed.")
    reader.join(timeout=1)

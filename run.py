import subprocess
import sys
import time


def main():
    processes = []

    try:
        print("Starting FastAPI backend...")

        backend = subprocess.Popen([
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ])

        processes.append(backend)

        time.sleep(1)

        print("Starting Discord bot...")

        bot = subprocess.Popen([
            sys.executable,
            "-m",
            "bot.main",
        ])

        processes.append(bot)

        print()
        print("================================")
        print("Skynet services are running")
        print("Backend: http://127.0.0.1:8000")
        print("Swagger: http://127.0.0.1:8000/docs")
        print("Discord bot: running")
        print("================================")

        for process in processes:
            process.wait()

    except KeyboardInterrupt:
        print("\nStopping services...")

        for process in processes:
            process.terminate()

        for process in processes:
            process.wait()

        print("All services stopped.")


if __name__ == "__main__":
    main()
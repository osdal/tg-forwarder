import os
import sys
import signal
import subprocess
import time
from pathlib import Path

PIDS_DIR = Path("pids")
PIDS_DIR.mkdir(exist_ok=True)

def get_pid_file(name: str) -> Path:
    return PIDS_DIR / f"{name}.pid"

def is_running(name: str) -> bool:
    """Проверяет, жив ли процесс по PID."""
    pid_file = get_pid_file(name)
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        # Проверка на Windows и Linux
        if sys.platform == "win32":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (ProcessLookupError, ValueError, OSError):
        return False

def kill_all_python_by_module(module_name: str) -> int:
    """Убивает ВСЕ python-процессы, содержащие module_name в командной строке."""
    if sys.platform != "win32":
        try:
            subprocess.run(["pkill", "-f", module_name], timeout=5)
            return 1
        except Exception:
            return 0
    
    killed = 0
    try:
        result = subprocess.run(
            ["wmic", "process", "where", f"name='python.exe'", "get", "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.split("\n"):
            if module_name in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    pid_str = parts[-1].strip()
                    if pid_str.isdigit():
                        try:
                            subprocess.run(["taskkill", "/F", "/T", "/PID", pid_str], capture_output=True, timeout=5)
                            killed += 1
                        except Exception:
                            pass
    except Exception:
        try:
            cmd = f"Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object {{ $_.CommandLine -like '*{module_name}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True, timeout=15)
            killed = 1
        except Exception:
            pass
    return killed

def start_process(name: str, module: str) -> tuple[bool, str]:
    """Запускает процесс, если он еще не запущен."""
    if is_running(name):
        return False, "Процесс уже запущен (PID файл)"
    
    # Убиваем "забытые" процессы перед запуском
    existing = kill_all_python_by_module(module)
    if existing > 0:
        time.sleep(1)

    cmd = [sys.executable, "-m", module]
    
    # Принудительно включаем UTF-8 для дочернего процесса, чтобы логи не ломались
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    log_file = open(f"{name}.log", "a", encoding="utf-8")
    
    kwargs = {
        "stdout": log_file,
        "stderr": log_file,
        "cwd": os.getcwd(),
        "env": env
    }
    
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    try:
        process = subprocess.Popen(cmd, **kwargs)
        get_pid_file(name).write_text(str(process.pid))
        return True, f"Процесс запущен (PID: {process.pid})"
    except Exception as e:
        return False, f"Ошибка запуска: {str(e)}"

def stop_process(name: str) -> tuple[bool, str]:
    """Останавливает процесс по PID."""
    pid_file = get_pid_file(name)
    if not pid_file.exists():
        return False, "Процесс не запущен"

    try:
        pid = int(pid_file.read_text().strip())
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=True, capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        
        pid_file.unlink() # Удаляем файл PID
        return True, "Процесс остановлен"
    except Exception as e:
        # Если процесса уже нет, просто чистим файл
        if pid_file.exists():
            pid_file.unlink()
        return False, f"Ошибка остановки: {str(e)}"
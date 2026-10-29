import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LABS = ROOT / "labs"


def run_script(relpath: str, timeout: int = 300) -> str:
    """labs/ 아래 스크립트를 그 폴더에서 실행하고 표준 출력을 돌려준다. 실패하면 테스트 실패."""
    path = LABS / relpath
    proc = subprocess.run([sys.executable, path.name], cwd=path.parent, capture_output=True,
                          text=True, timeout=timeout)
    assert proc.returncode == 0, f"{relpath} 실행 실패\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout


@pytest.fixture
def run():
    return run_script

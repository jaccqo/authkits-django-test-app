"""Install a supplied customer wheel into fresh, source-free reference hosts.

Run locally or in private CI. Never upload the wheel or generated environments to
this public repository. This does not activate a license or contact OAuth providers.
"""

import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import venv

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {"base": "", "mfa": "mfa", "api": "api", "social": "social", "api-social": "api,social"}


def run(command, cwd, environment):
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def smoke(wheel, profile, django):
    with tempfile.TemporaryDirectory(prefix=f"authkits-reference-{profile}-") as directory:
        root = Path(directory)
        host = root / "host"
        host.mkdir()
        for name in ("config", "templates", "static", "host_tests", "docs"):
            shutil.copytree(ROOT / name, host / name, ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("manage.py", "requirements.txt", ".env.example"):
            shutil.copy2(ROOT / name, host / name)
        environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("AUTHKITS_", "DJANGO_"))
            and key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"}
        }
        environment.update({
            "DJANGO_DEBUG": "1", "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
            "DJANGO_ALLOWED_HOSTS": "127.0.0.1,localhost,testserver",
            "AUTHKITS_ENTITLEMENT": "", "AUTHKITS_ENTITLEMENT_FILE": "",
            "AUTHKITS_API_ENABLED": "1" if "api" in profile else "0",
            "AUTHKITS_SOCIAL_ENABLED": "1" if "social" in profile else "0",
            "AUTHKITS_GITHUB_CLIENT_ID": "reference-test-id",
            "AUTHKITS_GITHUB_CLIENT_SECRET": "reference-test-secret",
            "AUTHKITS_GOOGLE_CLIENT_ID": "reference-test-id",
            "AUTHKITS_GOOGLE_CLIENT_SECRET": "reference-test-secret",
        })
        venv.create(root / "venv", with_pip=True)
        python = root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        extra = f"[{PROFILES[profile]}]" if PROFILES[profile] else ""
        command = [str(python), "-m", "pip", "install", "-r", "requirements.txt", str(wheel) + extra]
        if django:
            command.append("Django>=5.2,<5.3" if django == "5.2" else "Django>=6.0,<6.1")
        run(command, host, environment)
        # Confirm site-packages consumption, and that base/historical MFA do not pull SDKs.
        probe = (
            "import authkits, importlib.util, sys; from pathlib import Path; "
            "assert Path(authkits.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()); "
        )
        if profile in {"base", "mfa"}:
            probe += "assert importlib.util.find_spec('rest_framework') is None; assert importlib.util.find_spec('allauth') is None"
        run([str(python), "-c", probe], host, environment)
        if profile == "mfa":
            key = subprocess.check_output(
                [str(python), "-c", "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"],
                cwd=host, env=environment, text=True,
            ).strip()
            environment["AUTHKITS_TOTP_KEYS"] = key
        for arguments in (
            ["-m", "unittest", "discover", "-s", "host_tests", "-v"],
            ["-m", "compileall", "-q", "config", "host_tests", "manage.py"],
            ["manage.py", "migrate", "--noinput"],
            ["manage.py", "check"],
            ["manage.py", "test", "config", "-v", "1"],
        ):
            run([str(python), *arguments], host, environment)
        print(f"PASS: {profile} installed-wheel reference smoke", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path, help="Downloaded licensed .whl, stored outside this repo")
    parser.add_argument("--profile", choices=PROFILES, action="append", help="Repeat; default runs all five profiles")
    parser.add_argument("--django", choices=("5.2", "6.0"), help="Constrain the Django line; 6.0 requires Python 3.12+")
    args = parser.parse_args()
    wheel = args.wheel.expanduser().resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error("Supply an existing licensed .whl file.")
    for profile in args.profile or PROFILES:
        smoke(wheel, profile, args.django)


if __name__ == "__main__":
    main()

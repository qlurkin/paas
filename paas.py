import json
from subprocess import run
import os
import sys

HOME = os.path.expanduser("~")

PAAS_ROOT = os.path.join(HOME, "paas")

HELP = """
Usage: paas.py <command> <name> <params>

commands:
- create <name> <git>
- port <name> <host_port>:<container_port>
- start <name>
- stop <name>
- update <name>
- logs <name>
- status
"""


def app_root(name: str):
    return os.path.join(PAAS_ROOT, name)


def app_config_path(name: str):
    return os.path.join(app_root(name), "config.json")


def load_app_config(name: str):
    with open(app_config_path(name)) as file:
        config = json.load(file)
    return config


def save_app_config(name: str, config: dict):
    with open(app_config_path(name), "w") as file:
        json.dump(config, file)


def run_in_app_root(name: str, cmd: list[str]):
    cwd = os.getcwd()
    os.chdir(app_root(name))
    run(cmd)
    os.chdir(cwd)


def build(name: str):
    config = load_app_config(name)
    version = config["version"] + 1
    run_in_app_root(
        name,
        ["sudo", "docker", "build", "-t", f"{name}:{version}", config["repository"]],
    )
    config["version"] = version
    save_app_config(name, config)


def create(name: str, git: str):
    if not os.path.exists(PAAS_ROOT):
        os.makedirs(PAAS_ROOT)

    if name in os.listdir(PAAS_ROOT):
        raise ValueError("Name already used")

    os.makedirs(app_root(name))

    repository = os.path.splitext(os.path.basename(git))[0]

    config = {
        "name": name,
        "version": 0,
        "repository": repository,
        "ports": [],
    }

    save_app_config(name, config)
    with open(os.path.join(app_root(name), "env"), "w"):
        pass
    run_in_app_root(name, ["git", "clone", git])
    build(name)


def add_port(name: str, port: str):
    config = load_app_config(name)
    config["ports"].append(port)
    save_app_config(name, config)


def update(name):
    run_in_app_root(name, ["git", "pull"])
    build(name)
    stop(name)
    start(name)


def stop(name: str):
    run(
        [
            "sudo",
            "docker",
            "stop",
            name,
        ],
    )
    run(
        [
            "sudo",
            "docker",
            "rm",
            name,
        ],
    )


def start(name):
    config = load_app_config(name)
    ports = []
    for port in config["ports"]:
        ports.append("-p")
        ports.append(port)

    run_in_app_root(
        name,
        [
            "sudo",
            "docker",
            "run",
            "--env-file",
            "env",
        ]
        + ports
        + [
            "-d",
            "--name",
            name,
            "--restart",
            "unless-stopped",
            f"{name}:{config['version']}",
        ],
    )


def logs(name):
    run(["sudo", "docker", "logs", name])


def status():
    run(["sudo", "docker", "ps"])


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(HELP)
        sys.exit()

    cmd = sys.argv[1]

    if cmd == "status":
        status()
    else:
        name = sys.argv[2]
        if cmd == "create":
            git = sys.argv[2]
            create(name, git)
        elif cmd == "port":
            port = sys.argv[2]
            add_port(name, port)
        elif cmd == "update":
            update(name)
        elif cmd == "start":
            start(name)
        elif cmd == "stop":
            stop(name)
        elif cmd == "logs":
            logs(name)
        else:
            print(HELP)

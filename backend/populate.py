"""Run fake telemetry simulation for the Smart Factory backend.

Default mode sends data through the API so alert rules and WebSocket broadcasts
behave exactly like production traffic.

Examples:
    python populate.py --machines 20 --create-missing --duration 300
    python populate.py --machines 12 --create-missing --duration 0 --interval 2
"""

import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from urllib import error, request

from db.session import Base, SessionLocal, engine
from models.machine import Machine
from models.sensor_data import SensorData

API_DEFAULT = "http://localhost:8003"


@dataclass
class MachineState:
    """Keeps rolling process state for one machine."""

    machine_id: int
    name: str
    location: str
    production_count: int
    base_temp: float
    current_temp: float


def create_schema() -> None:
    """Create database schema if it does not already exist."""
    Base.metadata.create_all(bind=engine)


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 8):
    """Perform JSON HTTP request and return decoded JSON body."""
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = request.Request(url=url, data=body, method=method, headers=headers)
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else None


def ensure_machines_db(session, count: int) -> list[Machine]:
    """Ensure requested machines exist (DB mode support)."""
    query = session.query(Machine).order_by(Machine.id.asc())
    machines = query.all() if count <= 0 else query.limit(count).all()
    existing = len(machines)

    if count > 0 and existing < count:
        for index in range(existing + 1, count + 1):
            session.add(
                Machine(
                    name=f"Machine-{index:03d}",
                    location=f"Line {random.randint(1, 10)}",
                )
            )
        session.commit()
        machines = session.query(Machine).order_by(Machine.id.asc()).limit(count).all()

    return machines


def ensure_machines_api(api_base_url: str, count: int, create_missing: bool) -> list[dict]:
    """Load machines from API and optionally create missing ones through API."""
    if count <= 0:
        machines = http_json("GET", f"{api_base_url}/machines?skip=0&limit=1000") or []
        return machines

    machines = http_json("GET", f"{api_base_url}/machines?skip=0&limit={count}") or []
    existing = len(machines)

    if existing < count and create_missing:
        for index in range(existing + 1, count + 1):
            payload = {
                "name": f"Machine-{index:03d}",
                "location": f"Line {random.randint(1, 10)}",
            }
            http_json("POST", f"{api_base_url}/machines", payload)
        machines = http_json("GET", f"{api_base_url}/machines?skip=0&limit={count}") or []

    return machines


def initialize_machine_states(machines: list[dict]) -> list[MachineState]:
    """Build rolling state values for each machine."""
    states: list[MachineState] = []
    for machine in machines:
        base_temp = random.uniform(58.0, 70.0)
        states.append(
            MachineState(
                machine_id=int(machine["id"]),
                name=str(machine["name"]),
                location=str(machine["location"]),
                production_count=random.randint(0, 120),
                base_temp=base_temp,
                current_temp=base_temp,
            )
        )
    return states


def next_reading(state: MachineState) -> dict:
    """Generate the next sensor reading with occasional warnings/errors."""
    event = random.choices(
        ["normal", "warning", "error"],
        weights=[84, 12, 4],
        k=1,
    )[0]

    drift = random.uniform(-1.5, 1.5)
    state.current_temp = max(50.0, min(120.0, state.current_temp + drift))

    if event == "error":
        state.current_temp = random.uniform(90.0, 115.0)
        state.production_count = max(0, state.production_count - random.randint(0, 3))
    elif event == "warning":
        state.current_temp = max(state.current_temp, random.uniform(80.0, 92.0))
        state.production_count += random.randint(0, 3)
    else:
        state.current_temp = (state.current_temp + state.base_temp) / 2.0
        state.production_count += random.randint(2, 10)

    return {
        "machine_id": state.machine_id,
        "temperature": round(state.current_temp, 1),
        "status": event,
        "production_count": state.production_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def write_reading_db(session, payload: dict) -> SensorData:
    """Insert one reading directly in DB (legacy mode)."""
    sensor_data = SensorData(**payload)
    session.add(sensor_data)
    return sensor_data


def write_reading_api(api_base_url: str, payload: dict) -> dict:
    """Submit one reading through API (triggers alerts + WebSocket)."""
    return http_json("POST", f"{api_base_url}/sensor-data", payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate backend with fake telemetry data.")
    parser.add_argument(
        "--machines",
        type=int,
        default=20,
        help="Number of machines to create or use. Use 0 to include all existing machines.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Total simulation duration in seconds. Use 0 for infinite run.",
    )
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between generated samples.")
    parser.add_argument("--create-missing", action="store_true", help="Create machines if they do not exist.")
    parser.add_argument(
        "--mode",
        choices=["api", "db"],
        default="api",
        help="Write mode: api (real-time + alerts) or db (direct insert only).",
    )
    parser.add_argument("--api-base-url", default=API_DEFAULT, help="Base API URL for api mode.")
    args = parser.parse_args()

    create_schema()

    if args.mode == "api":
        try:
            machines = ensure_machines_api(args.api_base_url.rstrip("/"), args.machines, args.create_missing)
        except error.URLError as exc:
            raise SystemExit(
                f"Could not reach API at {args.api_base_url}. Start backend first or use --mode db.\n{exc}"
            ) from exc

        if not machines:
            raise SystemExit("No machines found. Use --create-missing to create them first.")

        states = initialize_machine_states(machines)
        run_forever = args.duration == 0
        start_ts = datetime.now(timezone.utc)
        print(
            f"Starting API simulator for {len(states)} machines at {args.api_base_url} "
            f"(interval={args.interval}s, duration={'infinite' if run_forever else str(args.duration) + 's'})"
        )

        while True:
            elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
            if not run_forever and elapsed >= args.duration:
                break

            for state in states:
                payload = next_reading(state)
                try:
                    created = write_reading_api(args.api_base_url.rstrip("/"), payload)
                    print(
                        f"[{created.get('timestamp')}] {state.name} status={created.get('status')} "
                        f"temp={created.get('temperature')} count={created.get('production_count')}"
                    )
                except error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="ignore")
                    print(f"API write failed for {state.name}: HTTP {exc.code} {detail}")
                except error.URLError as exc:
                    print(f"API write failed for {state.name}: {exc}")

            sleep(args.interval)

        print("Simulation complete.")
        return

    with SessionLocal() as session:
        machines = ensure_machines_db(session, args.machines) if args.create_missing else (
            (
                session.query(Machine).order_by(Machine.id.asc()).all()
                if args.machines <= 0
                else session.query(Machine).order_by(Machine.id.asc()).limit(args.machines).all()
            )
        )
        if not machines:
            raise SystemExit("No machines found. Use --create-missing to create them first.")

        machine_dicts = [{"id": m.id, "name": m.name, "location": m.location} for m in machines]
        states = initialize_machine_states(machine_dicts)
        run_forever = args.duration == 0
        start_ts = datetime.now(timezone.utc)
        print(
            f"Starting DB simulator for {len(states)} machines "
            f"(interval={args.interval}s, duration={'infinite' if run_forever else str(args.duration) + 's'})"
        )

        while True:
            elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
            if not run_forever and elapsed >= args.duration:
                break

            for state in states:
                payload = next_reading(state)
                row = write_reading_db(session, payload)
                print(
                    f"[{row.timestamp}] {state.name} status={row.status} "
                    f"temp={row.temperature} count={row.production_count}"
                )
            session.commit()
            sleep(args.interval)

        print("Simulation complete.")


if __name__ == "__main__":
    main()

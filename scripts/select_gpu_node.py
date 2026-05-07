#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys


PREFERRED_PARTITIONS = [
    "aoraki_gpu_A100_80GB",
    "aoraki_gpu_H100",
    # These partitions exist in the RTIS resource table, but currently have
    # restricted AllowQos values on this cluster. They are only considered when
    # --allow-restricted-qos is passed.
    "aoraki_gpu_RTX6000",
    "aoraki_gpu_H200",
]


def parse_mem_to_mb(value: str) -> int:
    match = re.fullmatch(r"(\d+)([KMGTP]?)", value.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid memory value: {value}")
    number = int(match.group(1))
    unit = match.group(2).upper()
    multipliers = {"": 1, "K": 1 / 1024, "M": 1, "G": 1024, "T": 1024 * 1024}
    return int(number * multipliers[unit])


def parse_tres_count(tres: str, key: str) -> int:
    generic_count: int | None = None
    typed_total = 0
    for part in tres.split(","):
        if part.startswith(f"{key}="):
            try:
                generic_count = int(part.rsplit("=", 1)[1])
            except ValueError:
                pass
            continue
        if not part.startswith(f"{key}:"):
            continue
        try:
            typed_total += int(part.rsplit("=", 1)[1])
        except ValueError:
            pass
    if generic_count is not None:
        return generic_count
    return typed_total


def parse_node(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for item in line.split():
        if "=" in item:
            key, value = item.split("=", 1)
            fields[key] = value
    return fields


def load_partition_qos() -> dict[str, str]:
    output = subprocess.check_output(["scontrol", "show", "partition", "-o"], text=True)
    partition_qos: dict[str, str] = {}
    for line in output.splitlines():
        fields = parse_node(line)
        name = fields.get("PartitionName")
        if name:
            partition_qos[name] = fields.get("AllowQos", "")
    return partition_qos


def choose_partition(
    partitions: str,
    partition_qos: dict[str, str],
    allow_restricted_qos: bool,
) -> str | None:
    available = set(partitions.split(","))
    for partition in PREFERRED_PARTITIONS:
        if partition not in available:
            continue
        if not allow_restricted_qos and partition_qos.get(partition) not in ("", "ALL"):
            continue
        if partition in available:
            return partition
    return None


def score_node(node: dict[str, str], partition: str, free_mem: int, free_gpu: int) -> tuple[int, int, int]:
    state = node.get("State", "")
    idle_bonus = 10_000 if state.startswith("IDLE") else 0
    partition_bonus = (len(PREFERRED_PARTITIONS) - PREFERRED_PARTITIONS.index(partition)) * 100
    return idle_bonus + partition_bonus + free_gpu, free_mem, int(node.get("CPUTot", "0"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Select an immediately usable Aoraki GPU node.")
    parser.add_argument("--mem", default="120G", help="Required memory, e.g. 120G.")
    parser.add_argument("--cpus", type=int, default=4, help="Required CPUs.")
    parser.add_argument("--format", choices=("sbatch", "human"), default="sbatch")
    parser.add_argument(
        "--allow-restricted-qos",
        action="store_true",
        help="Consider partitions whose AllowQos is not ALL.",
    )
    args = parser.parse_args()

    required_mem = parse_mem_to_mb(args.mem)
    partition_qos = load_partition_qos()
    output = subprocess.check_output(["scontrol", "show", "nodes", "-o"], text=True)
    candidates: list[tuple[tuple[int, int, int], dict[str, str], str, int, int]] = []

    for line in output.splitlines():
        node = parse_node(line)
        partitions = node.get("Partitions", "")
        if "aoraki_gpu" not in partitions:
            continue
        state = node.get("State", "")
        if any(bad in state for bad in ("DOWN", "DRAIN", "FAIL", "POWER", "RESERVED")):
            continue
        partition = choose_partition(partitions, partition_qos, args.allow_restricted_qos)
        if not partition:
            continue

        total_mem = int(node.get("RealMemory", "0"))
        allocated_mem = int(node.get("AllocMem", "0"))
        system_reserved_mem = int(node.get("MemSpecLimit", "0"))
        free_mem = total_mem - allocated_mem - system_reserved_mem
        total_gpu = parse_tres_count(node.get("CfgTRES", ""), "gres/gpu")
        allocated_gpu = parse_tres_count(node.get("AllocTRES", ""), "gres/gpu")
        free_gpu = total_gpu - allocated_gpu
        free_cpus = int(node.get("CPUTot", "0")) - int(node.get("CPUAlloc", "0"))

        if free_gpu < 1 or free_mem < required_mem or free_cpus < args.cpus:
            continue

        candidates.append((score_node(node, partition, free_mem, free_gpu), node, partition, free_mem, free_gpu))

    if not candidates:
        print(
            f"No currently free GPU node satisfies cpu_mem={args.mem}, cpus={args.cpus}. "
            "Submit without --nodelist or lower MEM if appropriate.",
            file=sys.stderr,
        )
        return 1

    _, node, partition, free_mem, free_gpu = sorted(
        candidates,
        key=lambda item: item[0],
        reverse=True,
    )[0]
    node_name = node["NodeName"]
    if args.format == "human":
        print(f"{node_name} partition={partition} free_gpu={free_gpu} free_mem_mb={free_mem}")
    else:
        print(f"--partition={partition} --nodelist={node_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

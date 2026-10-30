#!/usr/bin/env python3
"""Retry creating the second Always Free A1 instance until Oracle has capacity (user-approved 2026-10-17).

Runs on the Oracle host from cron every 10 minutes with the OCI SDK venv (~/oci_venv) and the API key in ~/.oci
(the private key never leaves the host). Each run:
  1. stops at once if ~/.arepo/oci_retry/DONE exists, or an instance named NAME already exists (not TERMINATED):
     it never creates a second copy;
  2. free-tier guards: refuses unless A1 cores used + OCPUS <= A1_CORE_LIMIT, A1 memory used + MEM_GB <=
     A1_MEM_LIMIT_GB, and boot-volume GB in use + BOOT_GB <= FREE_BLOCK_GB (no block volumes counted
     beyond what exists);
  3. tries AD-1 then AD-2 (AD-3 offers no A1), with the fixed free settings below;
  4. on "Out of host capacity" logs and exits 0; on success writes DONE, logs the OCID and notifies by ntfy.
Log: ~/arepo_collector/logs/oci-retry.log. Stop: `touch ~/.arepo/oci_retry/DONE` or remove the cron line.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import oci

NAME = "arepo-research"
SHAPE = "VM.Standard.A1.Flex"
OCPUS, MEM_GB = 1, 6
BOOT_GB, VPUS = 100, 10  # Balanced (10 VPU/GB); higher VPUs are not free
A1_CORE_LIMIT, A1_MEM_LIMIT_GB, FREE_BLOCK_GB = 2, 12, 200
ADS = ("XnXa:UK-LONDON-1-AD-1", "XnXa:UK-LONDON-1-AD-2")
SUBNET_NAME = "public-subnet"
SSH_PUB = Path("~/.arepo/oci_retry/ssh_pub").expanduser()
STATE = Path("~/.arepo/oci_retry").expanduser()


def log(**kw) -> None:
    kw["at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(json.dumps(kw, sort_keys=True), flush=True)


def notify(headline: str, line: str) -> None:
    try:
        subprocess.run(["/home/opc/arepo/.venv/bin/python", "scripts/arepo_notify.py", "send", "--type", "milestone",
                        "--severity", "high", "--headline", headline, "--line", line, "--dedupe-key",
                        "oci-retry-" + headline[:20]], cwd="/home/opc/arepo/backend", timeout=60,
                       capture_output=True, check=False)
    except Exception:  # noqa: BLE001 - a failed alert must not fail the run
        pass


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=True)
    if (STATE / "DONE").exists():
        return 0
    cfg = oci.config.from_file()
    t = cfg["tenancy"]
    comp = oci.core.ComputeClient(cfg)
    bs = oci.core.BlockstorageClient(cfg)
    vn = oci.core.VirtualNetworkClient(cfg)
    insts = [i for i in comp.list_instances(t).data if i.lifecycle_state != "TERMINATED"]
    if any(i.display_name == NAME for i in insts):
        (STATE / "DONE").write_text("instance already exists\n")
        log(event="exists", note="instance already present; retry stopped")
        return 0
    a1 = [i for i in insts if i.shape == SHAPE]
    cores = sum(float(i.shape_config.ocpus) for i in a1)
    mem = sum(float(i.shape_config.memory_in_gbs) for i in a1)
    boot = sum(b.size_in_gbs for ad in ADS + ("XnXa:UK-LONDON-1-AD-3",)
               for b in bs.list_boot_volumes(availability_domain=ad, compartment_id=t).data
               if b.lifecycle_state != "TERMINATED")
    block = sum(v.size_in_gbs for v in bs.list_volumes(compartment_id=t).data if v.lifecycle_state != "TERMINATED")
    if "--check" in sys.argv:  # read-only: print what the guards see, launch nothing
        log(event="check", instances=[i.display_name for i in insts], cores=cores, mem=mem, boot=boot, block=block,
            would_launch=cores + OCPUS <= A1_CORE_LIMIT and mem + MEM_GB <= A1_MEM_LIMIT_GB
            and boot + block + BOOT_GB <= FREE_BLOCK_GB)
        return 0
    if cores + OCPUS > A1_CORE_LIMIT or mem + MEM_GB > A1_MEM_LIMIT_GB or boot + block + BOOT_GB > FREE_BLOCK_GB:
        log(event="refused_free_tier_guard", cores=cores, mem=mem, boot=boot, block=block)
        return 0
    subnet = next(s for s in vn.list_subnets(t).data if s.display_name == SUBNET_NAME)
    image = comp.list_images(t, operating_system="Oracle Linux", operating_system_version="9", shape=SHAPE,
                             sort_by="TIMECREATED", sort_order="DESC").data[0]
    for ad in ADS:
        details = oci.core.models.LaunchInstanceDetails(
            availability_domain=ad, compartment_id=t, display_name=NAME, shape=SHAPE,
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=OCPUS, memory_in_gbs=MEM_GB),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                image_id=image.id, boot_volume_size_in_gbs=BOOT_GB, boot_volume_vpus_per_gb=VPUS),
            create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=subnet.id, assign_public_ip=True),
            metadata={"ssh_authorized_keys": SSH_PUB.read_text().strip()},
        )
        try:
            r = comp.launch_instance(details)
        except oci.exceptions.ServiceError as e:
            log(event="no_capacity" if "capacity" in str(e.message).lower() else "error", ad=ad[-4:],
                status=e.status, code=e.code, message=str(e.message)[:160])
            time.sleep(5)
            continue
        (STATE / "DONE").write_text(f"{r.data.id}\n")
        log(event="created", ad=ad[-4:], id=r.data.id, image=image.display_name)
        notify("Second Oracle server created", f"{NAME} in {ad[-4:]} (1 OCPU, 6 GB, 100 GB, Always Free). "
               "Claude will set it up next session.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

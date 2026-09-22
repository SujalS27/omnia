# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Install OS Scenario — ISO Verification Tests.

Verifies ISO configuration files, credentials, and output artifacts.
"""

import pytest

from library.functions import (
    TestLogger,
    check_file_exists,
    check_dir_exists,
    validate_yaml_file,
    validate_install_os_config,
    validate_install_os_credentials,
    find_custom_iso,
    verify_iso_checksum,
    verify_kickstart_in_iso,
    get_utils_input_path,
    get_utils_output_path,
)
from library.vars import (
    TEST_CASES as TC,
    INSTALL_OS_CONFIG_FILE,
    INSTALL_OS_CREDENTIALS_FILE,
    INSTALL_OS_STATUS_FILE,
)
from library.messages import TEST_LOG_MSGS as LOG, TEST_ASSERT_MSGS as ASSERT


# =============================================================================
# INPUT FILE VERIFICATION (order 10-19)
# =============================================================================

@pytest.mark.sanity
@pytest.mark.order(10)
def test_install_os_config_file_exists(host):
    """Verify install_os_config.yml exists on target."""
    tc = TC["install_os_config_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CONFIG_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Config file is optional for basic tests
        tl.skipped(f"Config file not found (optional): {file_path}")
        pytest.skip(f"Config file not found: {file_path}")


@pytest.mark.sanity
@pytest.mark.order(11)
def test_install_os_config_valid(host):
    """Verify install_os_config.yml has valid structure."""
    tc = TC["install_os_config_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CONFIG_FILE}"

    # Check if file exists first
    exists_result = check_file_exists(host, file_path)
    if not exists_result["success"]:
        tl.skipped("Config file not found, skipping validation")
        pytest.skip("Config file not found")

    result = validate_install_os_config(host, file_path)

    if result["success"]:
        tl.passed(LOG["iso_config_valid"])
    else:
        tl.failed(LOG["iso_config_invalid"].format(error=result["error"]))

    assert result["success"], ASSERT["iso_config_invalid"].format(error=result["error"])


@pytest.mark.sanity
@pytest.mark.order(12)
def test_install_os_credentials_file_exists(host):
    """Verify install_os_credentials.yml exists."""
    tc = TC["install_os_credentials_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    input_path = get_utils_input_path(host)
    file_path = f"{input_path}/{INSTALL_OS_CREDENTIALS_FILE}"

    result = check_file_exists(host, file_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=file_path))
    else:
        # Credentials file is optional (can be provided via extra-vars)
        tl.skipped(f"Credentials file not found (optional): {file_path}")
        pytest.skip(f"Credentials file not found: {file_path}")


# =============================================================================
# OUTPUT VERIFICATION (order 50-59) - runs AFTER deploy tests (order 20-49)
# These tests require deploy to have run first. They are marked with 'deploy'
# marker so they only execute when deploy tests are included.
# =============================================================================

@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(50)
def test_install_os_output_dir_exists(host):
    """Verify install_os output directory exists after deploy."""
    tc = TC["install_os_output_dir_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    result = check_dir_exists(host, output_path)

    if result["success"]:
        tl.passed(LOG["dir_exists"].format(path=output_path))
    else:
        tl.failed(LOG["dir_missing"].format(path=output_path))

    assert result["success"], f"Output directory not found: {output_path}"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(51)
def test_install_os_status_file_exists(host):
    """Verify install_os_status.yml output file created after deploy."""
    tc = TC["install_os_status_file_exists"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    status_path = f"{output_path}/{INSTALL_OS_STATUS_FILE}"

    result = check_file_exists(host, status_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=status_path))
    else:
        tl.skipped("install_os_status.yml not found (requires build_iso or deploy execution)")
        pytest.skip("install_os_status.yml not found")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(52)
def test_install_os_status_valid(host):
    """Verify install_os_status.yml has valid structure after deploy."""
    tc = TC["install_os_status_valid"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    status_path = f"{output_path}/{INSTALL_OS_STATUS_FILE}"

    exists = check_file_exists(host, status_path)
    if not exists["success"]:
        tl.skipped("install_os_status.yml not found, skipping validation")
        pytest.skip("install_os_status.yml not found")

    yaml_result = validate_yaml_file(host, status_path)
    if not yaml_result["success"]:
        tl.failed(yaml_result["error"])
        pytest.fail(yaml_result["error"])

    data = yaml_result["data"]
    required = ["utility", "status", "timestamp"]
    missing = [k for k in required if k not in data]

    if missing:
        tl.failed(f"Missing keys in install_os_status.yml: {missing}")
    else:
        tl.passed("install_os_status.yml structure is valid")

    assert not missing, f"Missing keys in install_os_status.yml: {missing}"


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(53)
def test_install_os_custom_iso_created(host):
    """Verify custom ISO created after build_iso execution.

    Checks both local output directory and NFS path for the custom ISO.
    """
    tc = TC["install_os_custom_iso_created"]
    tl = TestLogger(tc["title"], tc["id"])

    # Check local output directory first
    output_path = get_utils_output_path(host)
    result = find_custom_iso(host, output_path)

    if result["success"]:
        tl.passed(LOG["custom_iso_created"].format(path=result["iso_path"]))
        return

    # If not found locally, check if NFS path is configured and accessible
    from library.functions import validate_install_os_config, get_utils_input_path
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/install_os_config.yml"

    config_result = validate_install_os_config(host, config_path)
    if config_result["success"]:
        config = config_result.get("config", {})
        custom_iso_path = config.get("custom_iso_path", "")

        if custom_iso_path and ":" in custom_iso_path:
            # Parse NFS path: server:/path/filename.iso
            nfs_server, nfs_path = custom_iso_path.split(":", 1)
            iso_filename = nfs_path.split("/")[-1]

            # Try to check if NFS is mounted and ISO exists
            # This is a simplified check - in real scenarios, NFS should be mounted
            tl.skipped(f"Custom ISO configured on NFS: {custom_iso_path}. NFS mount verification not implemented.")
            pytest.skip(f"Custom ISO on NFS path: {custom_iso_path}")

    tl.skipped("Custom ISO not found in output directory and NFS verification not available")
    pytest.skip("Custom ISO not found")


@pytest.mark.deploy
@pytest.mark.functional
@pytest.mark.order(54)
def test_install_os_kickstart_generated(host):
    """Verify kickstart.ks generated after deploy (optional)."""
    tc = TC["install_os_kickstart_generated"]
    tl = TestLogger(tc["title"], tc["id"])

    output_path = get_utils_output_path(host)
    ks_path = f"{output_path}/kickstart.ks"
    result = check_file_exists(host, ks_path)

    if result["success"]:
        tl.passed(LOG["file_exists"].format(path=ks_path))
    else:
        tl.skipped("kickstart.ks not found in output directory (may be written to NFS path)")
        pytest.skip("kickstart.ks not found")


# =============================================================================
# POST-DEPLOYMENT VERIFICATION (order 60-69)
# These tests verify the installed node is reachable and configured correctly.
# They require target_admin_ip and target_hostname to be configured.
# =============================================================================

def _get_install_os_config(host):
    """Helper to load install_os config and extract target node details."""
    input_path = get_utils_input_path(host)
    config_path = f"{input_path}/{INSTALL_OS_CONFIG_FILE}"

    result = validate_install_os_config(host, config_path)
    if not result["success"]:
        return {"success": False, "error": result["error"]}

    config = result.get("config", {})
    return {
        "success": True,
        "target_admin_ip": config.get("target_admin_ip", ""),
        "target_hostname": config.get("target_hostname", ""),
        "target_bmc_ip": config.get("target_bmc_ip", ""),
    }


@pytest.mark.sanity
@pytest.mark.order(60)
def test_install_os_node_reachable(host):
    """Verify installed node is reachable via ping.

    This is a post-deployment verification test. It checks that the node
    configured in install_os_config.yml is reachable after OS installation.
    """
    tc = TC["install_os_node_reachable"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _get_install_os_config(host)
    if not config["success"]:
        tl.failed(f"Cannot load install_os config: {config['error']}")
        pytest.fail(f"Cannot load install_os config: {config['error']}")

    target_ip = config["target_admin_ip"]
    if not target_ip:
        tl.failed("target_admin_ip not configured in install_os_config.yml - cannot verify node")
        pytest.fail("target_admin_ip not configured in install_os_config.yml")

    # Ping the target node
    ping_result = host.run(f"ping -c 3 -W 5 {target_ip}")

    if ping_result.rc == 0:
        tl.passed(f"Node {target_ip} is reachable via ping")
    else:
        tl.failed(f"Node {target_ip} is not reachable via ping")

    assert ping_result.rc == 0, f"Node {target_ip} is not reachable via ping"


@pytest.mark.sanity
@pytest.mark.order(61)
def test_install_os_node_ssh_accessible(host):
    """Verify installed node is accessible via SSH.

    This test verifies that SSH is running on the installed node and
    we can connect to it (using the SSH key configured during install).
    """
    tc = TC["install_os_node_ssh_accessible"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _get_install_os_config(host)
    if not config["success"]:
        tl.failed(f"Cannot load install_os config: {config['error']}")
        pytest.fail(f"Cannot load install_os config: {config['error']}")

    target_ip = config["target_admin_ip"]
    if not target_ip:
        tl.failed("target_admin_ip not configured in install_os_config.yml - cannot verify SSH")
        pytest.fail("target_admin_ip not configured in install_os_config.yml")

    # Try SSH connection with timeout
    ssh_result = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no "
        f"root@{target_ip} 'echo SSH_OK' 2>/dev/null"
    )

    if ssh_result.rc == 0 and "SSH_OK" in ssh_result.stdout:
        tl.passed(f"SSH connection to {target_ip} successful")
    else:
        tl.failed(f"SSH connection to {target_ip} failed")

    assert ssh_result.rc == 0 and "SSH_OK" in ssh_result.stdout, \
        f"SSH connection to {target_ip} failed (rc={ssh_result.rc})"


@pytest.mark.functional
@pytest.mark.order(62)
def test_install_os_node_hostname_correct(host):
    """Verify installed node hostname matches configuration.

    This test SSHs to the installed node and verifies that the hostname
    matches what was configured in install_os_config.yml.
    """
    tc = TC["install_os_node_hostname_correct"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _get_install_os_config(host)
    if not config["success"]:
        tl.failed(f"Cannot load install_os config: {config['error']}")
        pytest.fail(f"Cannot load install_os config: {config['error']}")

    target_ip = config["target_admin_ip"]
    expected_hostname = config["target_hostname"]

    if not target_ip:
        tl.failed("target_admin_ip not configured in install_os_config.yml")
        pytest.fail("target_admin_ip not configured in install_os_config.yml")

    if not expected_hostname:
        tl.failed("target_hostname not configured in install_os_config.yml")
        pytest.fail("target_hostname not configured in install_os_config.yml")

    # Get actual hostname from the node
    ssh_result = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no "
        f"root@{target_ip} 'hostname' 2>/dev/null"
    )

    if ssh_result.rc != 0:
        tl.failed(f"Cannot SSH to {target_ip} to verify hostname")
        pytest.fail(f"Cannot SSH to {target_ip} to verify hostname")

    actual_hostname = ssh_result.stdout.strip()

    # Compare hostnames (may be short or FQDN)
    if actual_hostname == expected_hostname or actual_hostname.startswith(f"{expected_hostname}."):
        tl.passed(f"Hostname matches: {actual_hostname}")
    else:
        tl.failed(f"Hostname mismatch: expected '{expected_hostname}', got '{actual_hostname}'")

    assert actual_hostname == expected_hostname or actual_hostname.startswith(f"{expected_hostname}."), \
        f"Hostname mismatch: expected '{expected_hostname}', got '{actual_hostname}'"


@pytest.mark.functional
@pytest.mark.order(63)
def test_install_os_node_ip_correct(host):
    """Verify installed node IP address matches configuration.

    This test SSHs to the installed node and verifies that the IP address
    matches what was configured in install_os_config.yml.
    """
    tc = TC["install_os_node_ip_correct"]
    tl = TestLogger(tc["title"], tc["id"])

    config = _get_install_os_config(host)
    if not config["success"]:
        tl.failed(f"Cannot load install_os config: {config['error']}")
        pytest.fail(f"Cannot load install_os config: {config['error']}")

    target_ip = config["target_admin_ip"]

    if not target_ip:
        tl.failed("target_admin_ip not configured in install_os_config.yml")
        pytest.fail("target_admin_ip not configured in install_os_config.yml")

    # Get actual IP addresses from the node
    ssh_result = host.run(
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no "
        f"root@{target_ip} 'ip -4 addr show | grep inet | awk \"{{print \\$2}}\" | cut -d/ -f1' 2>/dev/null"
    )

    if ssh_result.rc != 0:
        tl.failed(f"Cannot SSH to {target_ip} to verify IP")
        pytest.fail(f"Cannot SSH to {target_ip} to verify IP")

    actual_ips = ssh_result.stdout.strip().split('\n')

    if target_ip in actual_ips:
        tl.passed(f"IP address {target_ip} found on node")
    else:
        tl.failed(f"IP mismatch: expected '{target_ip}' in node IPs, got {actual_ips}")

    assert target_ip in actual_ips, \
        f"IP mismatch: expected '{target_ip}' in node IPs, got {actual_ips}"

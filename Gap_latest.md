# Omnia 2.2 → 2.3 Gap Analysis Report

**Date:** October 2026  
**Domains:** Discovery, Image Build Manager  
**Prepared for:** Omnia 2.3 Domain Completion Plan

---

## Executive Summary

This report provides a comprehensive gap analysis between Omnia 2.2 and 2.3 for the **Discovery** and **Image Build Manager** domains, covering both source code and test automation.

| Domain | Source Code Gap | Test Automation Gap |
|--------|-----------------|---------------------|
| Discovery | **No Gaps Found** (2.3 is a superset of 2.2) | **Gaps Found** (9 tests in 2.2 not in 2.3) |
| Image Build Manager | **No Gaps Found** (2.3 is a superset of 2.2) | **No Gaps Found** (2.3 is a superset of 2.2) |

---

# Part 1: Discovery Domain

## 1.1 Source Code Gap Analysis

### 2.2 Discovery Source Structure
**Location:** `/root/omnia_2.2/omnia/discovery/`

| Component | Files |
|-----------|-------|
| Main Playbook | `discovery.yml` |
| Role: ome_discovery | 8 files (tasks, vars, defaults) |
| **Total Files** | **10 files** |

**2.2 Tasks:**
- `get_ome_credentials.yml` - OME credential handling
- `collect_inventory.yml` - Collect server inventory from OME
- `generate_pxe_mapping.yml` - Generate PXE mapping file
- `generate_discovery_report.yml` - Generate BMC discovery report

### 2.3 Discovery Source Structure
**Location:** `/root/dell_om/omnia/src/discovery/`

| Component | Files |
|-----------|-------|
| Playbooks | 7 files (cleanup, credentials, execute, precheck, prepare, validate, discovery.yml) |
| Plugins/Modules | 6 Python modules |
| Validation Framework | 5 Python files |
| Roles | 7 roles (cleanup, common, credentials, setup, ome_discovery, precheck_environment, validate_discovery_input) |
| Input Files | 2 files (discovery_config.yml, network_spec.yml) |
| **Total Files** | **68 files** |

### Source Code Gap Analysis Result: **NO GAPS FOUND**

**Rationale:**
All 2.2 functionality is preserved and enhanced in 2.3:

| 2.2 Feature | 2.3 Equivalent | Status |
|-------------|----------------|--------|
| `get_ome_credentials.yml` | `roles/discovery_credentials/` + `roles/ome_discovery/tasks/get_ome_credentials.yml` | ✅ Enhanced |
| `collect_inventory.yml` | `roles/ome_discovery/tasks/collect_inventory.yml` | ✅ Preserved |
| `generate_pxe_mapping.yml` | `roles/ome_discovery/tasks/generate_pxe_mapping.yml` + `plugins/modules/generate_pxe_mapping.py` | ✅ Enhanced |
| `generate_discovery_report.yml` | `roles/ome_discovery/tasks/generate_discovery_report.yml` + `plugins/modules/generate_discovery_report.py` | ✅ Enhanced |
| OME connectivity check | `roles/discovery_common/tasks/check_ome_connectivity.yml` | ✅ New (extracted) |

**2.3 Enhancements over 2.2:**
1. **Modular playbook structure** - Separate playbooks for cleanup, credentials, execute, precheck, prepare, validate
2. **Python validation framework** - `plugins/module_utils/discovery_validation/` with schema validation
3. **Custom Ansible modules** - `validate_credentials.py`, `validate_discovery_config.py`, `validate_system_environment.py`
4. **Discovery status file** - Success/failure status written to `discovery_status.yml`
5. **Cleanup role** - `roles/discovery_cleanup/` for cleaning credentials, logs, output
6. **Input validation role** - `roles/validate_discovery_input/`
7. **Precheck environment role** - `roles/precheck_environment/`

---

## 1.2 Test Automation Gap Analysis

### 2.2 Discovery Test Structure
**Location:** `/root/omnia_2.2_test/omnia-containers/molecule/discovery/tests/sanity/test_discovery.py`

| Test # | Test Name | Description |
|--------|-----------|-------------|
| 1 | `test_bmc_pxe_mapping_created` | Verify BMC PXE mapping file created with timestamp |
| 2 | `test_pxe_mapping_columns` | Verify PXE mapping file has all required columns |
| 3 | `test_functional_groups_supported` | Verify all functional groups are Omnia-supported |
| 4 | `test_ip_correlation` | Verify ADMIN_IP and IB_IP correlation with BMC_IP |
| 5 | `test_parent_service_tag` | Verify PARENT_SERVICE_TAG rules for slurm_node groups |
| 6 | `test_ome_static_groups_match` | Verify OME static groups match PXE mapping functional groups |
| 7 | `test_ome_unassigned_devices` | Verify OME devices without static group assignment |
| 8 | `test_admin_mac_validation` | Verify ADMIN_MAC matches OME first active non-iDRAC NIC |
| 9 | `test_ib_nic_name_validation` | Verify IB_NIC_NAME matches OME first active InfiniBand NIC |

**Total 2.2 Tests:** 9 tests

### 2.3 Discovery Test Structure
**Location:** `/root/dell_om/omnia/test/discovery/`

| Suite | Test Cases |
|-------|------------|
| **fvt/precheck** | `deploy_precheck` (E001) |
| **fvt/validate** | `deploy_validate` (E001), `input_config_exists` (V001), `network_spec_exists` (V002), `credentials_present` (V003) |
| **fvt/credentials** | `deploy_credentials` (E001) |
| **fvt/execute** | `deploy_execute` (E001) |
| **fvt/execute/output** | `output_dir_exists` (V001), `pxe_mapping_created` (V002), `pxe_mapping_columns` (V003), `pxe_mapping_has_rows` (V004), `pxe_mapping_symlink` (V005), `discovery_report_created` (V006) |
| **fvt/discovery** | `deploy_discovery` (E001) |
| **fvt/cleanup** | `deploy_cleanup` (E001-E004), `output_dir_removed` (V001), `credentials_removed` (V002), `credentials_preserved` (V003), `pxe_mapping_files_removed` (V004), `discovery_report_files_removed` (V005), `status_files_removed` (V006), `log_files_removed` (V007), `log_files_preserved` (V008) |
| **nft** | `precheck_performance` (NFT_001), `execute_performance` (NFT_002), `cleanup_performance` (NFT_003), `precheck_idempotent` (NFT_004), `cleanup_idempotent` (NFT_005) |
| **ut** | `test_discovery_config_validator.py`, `test_input_validation_schema.py`, `test_standalone_independence.py` |

**Total 2.3 Tests:** 29 test cases registered

### Test Automation Gap Analysis Result: **GAPS FOUND**

| 2.2 Test | 2.3 Equivalent | Gap Status |
|----------|----------------|------------|
| `test_bmc_pxe_mapping_created` | `pxe_mapping_created` (V002) | ✅ Covered |
| `test_pxe_mapping_columns` | `pxe_mapping_columns` (V003) | ✅ Covered |
| `test_functional_groups_supported` | **NOT FOUND** | ❌ **GAP** |
| `test_ip_correlation` | **NOT FOUND** | ❌ **GAP** |
| `test_parent_service_tag` | **NOT FOUND** | ❌ **GAP** |
| `test_ome_static_groups_match` | **NOT FOUND** | ❌ **GAP** |
| `test_ome_unassigned_devices` | **NOT FOUND** | ❌ **GAP** |
| `test_admin_mac_validation` | **NOT FOUND** | ❌ **GAP** |
| `test_ib_nic_name_validation` | **NOT FOUND** | ❌ **GAP** |

### Discovery Test Gaps Summary

**7 tests from 2.2 are NOT present in 2.3:**

| Gap # | 2.2 Test | Description | Priority |
|-------|----------|-------------|----------|
| 1 | `test_functional_groups_supported` | Verify all functional groups in PXE mapping are Omnia-supported | High |
| 2 | `test_ip_correlation` | Verify ADMIN_IP/IB_IP correlation with BMC_IP based on network_spec.yml | High |
| 3 | `test_parent_service_tag` | Verify PARENT_SERVICE_TAG rules for slurm_node groups | Medium |
| 4 | `test_ome_static_groups_match` | Verify OME static groups match PXE mapping functional groups | High |
| 5 | `test_ome_unassigned_devices` | Verify OME devices without static group assignment | Medium |
| 6 | `test_admin_mac_validation` | Verify ADMIN_MAC matches OME first active non-iDRAC NIC | High |
| 7 | `test_ib_nic_name_validation` | Verify IB_NIC_NAME matches OME first active InfiniBand NIC | Medium |

**Note:** These tests require OME connectivity and validate the PXE mapping output against live OME data.

---

# Part 2: Image Build Manager Domain

## 2.1 Source Code Gap Analysis

### 2.2 Image Build Source Structure
**Location:** `/root/omnia_2.2/omnia/build_image_x86_64/` and `/root/omnia_2.2/omnia/build_image_aarch64/`

| Component | x86_64 Files | aarch64 Files |
|-----------|--------------|---------------|
| Main Playbook | 1 | 1 |
| Role: fetch_packages | 6 | 6 |
| Role: image_creation | 6 | 5 |
| Role: prepare_arm_node | N/A | 2 |
| **Total Files** | **16 files** | **18 files** |

**2.2 Tasks (x86_64):**
- `fetch_packages.yml` - Fetch packages from repos
- `fetch_pulp_repos.yml` - Fetch Pulp repositories
- `build_stream_prerequisite.yml` - Build stream prerequisites
- `check_x86_64_fg.yml` - Check functional groups
- `build_base_image.yml` - Build base image
- `build_compute_image.yml` - Build compute image
- `set_s3_acl.yml` - Set S3 ACL
- `preflight_selinux_check.yml` - SELinux preflight check

### 2.3 Image Build Manager Source Structure
**Location:** `/root/dell_om/omnia/src/image_build_manager/`

| Component | Files |
|-----------|-------|
| Playbooks | 8 files (build, cleanup, credentials, precheck, prepare, validate) |
| Roles | 7 roles (build_os_images, cleanup_build_artifacts, collect_build_credentials, precheck_build_environment, prepare_build_environment, validate_build_config, validate_build_input) |
| Input Files | 2 files (image_build_config.yml, package_groups.yml) |
| **Total Files** | **97 files** |

### Source Code Gap Analysis Result: **NO GAPS FOUND**

**Rationale:**
All 2.2 functionality is preserved and consolidated in 2.3:

| 2.2 Feature | 2.3 Equivalent | Status |
|-------------|----------------|--------|
| `build_image_x86_64.yml` | `playbooks/build/build_image_x86_64.yml` | ✅ Preserved |
| `build_image_aarch64.yml` | `playbooks/build/build_image_aarch64.yml` | ✅ Preserved |
| `fetch_packages` role | `roles/build_os_images/` (consolidated) | ✅ Enhanced |
| `image_creation` role | `roles/build_os_images/` (consolidated) | ✅ Enhanced |
| `prepare_arm_node` role | `roles/prepare_build_environment/` | ✅ Enhanced |
| `build_base_image.yml` | `roles/build_os_images/tasks/build_base_image_x86_64.yml` + `build_base_image_aarch64.yml` | ✅ Enhanced |
| `build_compute_image.yml` | `roles/build_os_images/tasks/build_compute_image_x86_64.yml` + `build_compute_image_aarch64.yml` | ✅ Enhanced |
| `set_s3_acl.yml` | `roles/build_os_images/tasks/set_s3_acl.yml` | ✅ Preserved |
| `preflight_selinux_check.yml` | `roles/build_os_images/tasks/preflight_selinux_check.yml` | ✅ Preserved |

**2.3 Enhancements over 2.2:**
1. **Unified domain** - x86_64 and aarch64 consolidated into single `image_build_manager` domain
2. **Modular playbook structure** - Separate playbooks for build, cleanup, credentials, precheck, prepare, validate
3. **Cleanup role** - `roles/cleanup_build_artifacts/` with granular cleanup (credentials, domain_data, logs, minio, registry, s3cmd, images)
4. **Validation framework** - `roles/validate_build_config/` and `roles/validate_build_input/`
5. **Precheck role** - `roles/precheck_build_environment/`
6. **Build status tracking** - `write_build_status.yml` for success/failure tracking
7. **Image verification** - `verify_compute_image_x86_64.yml` and `verify_compute_image_aarch64.yml`
8. **Hash caching** - `save_compute_image_hashes.yml` for catalog reuse
9. **Registry configuration** - `configure_registry.yml`
10. **Dictionary validation** - `validate_dictionary_hits.yml` for catalog reuse

---

## 2.2 Test Automation Gap Analysis

### 2.2 Image Build Test Structure
**Location:** `/root/omnia_2.2_test/omnia-containers/molecule/build_image_x86_64/tests/sanity/test_build_image_x86_64.py`
**Location:** `/root/omnia_2.2_test/omnia-containers/molecule/build_image_aarch64/tests/sanity/test_build_image_aarch64.py`

| Test # | Test Name | Description |
|--------|-----------|-------------|
| 1 | `test_build_stream_job_stage` | Verify build_stream pipeline stage completed |
| 2 | `test_functional_group_content` | Verify functional_groups_config.yml exists and contains all roles/groups |
| 3 | `test_regctl_registry_images` | Verify base and compute images in regctl registry |
| 4 | `test_s3_bucket_images` | Verify all images pushed to S3 bucket |
| 5 | `test_all_image_packages` | Verify all packages installed in S3 images |

**Total 2.2 Tests:** 5 tests per architecture (10 total)

### 2.3 Image Build Manager Test Structure
**Location:** `/root/dell_om/omnia/test/image_build_manager/`

| Suite | Test Cases |
|-------|------------|
| **fvt/validate** | `deploy_validate` (E001), `input_config_exists` (V001), `credentials_present_vl` (V002), `repo_ssl_verify_config` (V003), `repo_ssl_verify_applied` (V004) |
| **fvt/precheck** | `deploy_precheck` (E001), `target_connectivity` (V001), `env_vars_present` (V002), `hostname_domain` (V003), `admin_ip_assigned` (V004), `omnia_setup` (V005) |
| **fvt/prepare** | `deploy_prepare` (E001), `storage_backend` (V001), `registry_container_running` (V002), `services_active` (V003), `firewall_ports_open` (V004), `s3cmd_configured` (V005), `registry_reachable` (V006), `s3_buckets_created` (V007), `registry_image_version` (V008) |
| **fvt/build** | `deploy_build` (E001), `s3_images_x86_64` (V006), `s3_images_aarch64` (V007), `registry_images_x86_64` (V008), `registry_images_aarch64` (V009), `build_status_file` (V010), `functional_groups_x86_64` (V011), `functional_groups_aarch64` (V012), `packages_x86_64` (V018), `packages_aarch64` (V019) |
| **fvt/build/aarch64** | `aarch64_ssh_connectivity` (V001), `aarch64_architecture` (V002), `aarch64_work_dirs` (V003), `aarch64_builder_image` (V004), `aarch64_regctl_installed` (V005) |
| **fvt/build/naming** | `registry_naming_ib_x86_64` (V013), `s3_naming_ib_x86_64` (V014), `registry_naming_th_x86_64` (V015), `s3_naming_th_x86_64` (V016), `artifact_suffix_isolation` (V017) |
| **fvt/build/catalog_reuse** | `catalog_first_build` (V001), `catalog_dictionary_reuse` (V002), `catalog_selective_package_rebuild` (V003), `catalog_repository_change_rebuild` (V004), `catalog_force_rebuild` (V005), `catalog_missing_artifact_rebuild` (V006), `catalog_switch_to_thrillhouse` (V007), `catalog_switch_to_image_builder` (V008), `catalog_versioned_output` (V009), `config_mode_cache_isolation` (V010), `catalog_suite_restores_target_state` (V011) |
| **fvt/cleanup** | `deploy_cleanup` (E001), `containers_removed` (V001), `services_removed` (V002), `firewall_ports_closed` (V003), `s3_artifacts_removed` (V004), `s3cfg_removed` (V005), `build_output_removed` (V006), `registry_cleaned` (V007), `credentials_removed` (V008) |
| **fvt/cleanup_images** | `deploy_cleanup_images` (E001), `s3_images_cleaned` (V001), `registry_images_cleaned` (V002) |
| **nft** | `prepare_performance` (NFT_001), `build_performance` (NFT_002), `cleanup_performance` (NFT_003), `prepare_idempotent` (NFT_004), `minio_quadlet_permissions` (NFT_SECURITY_001), `s3cfg_permissions` (NFT_SECURITY_002) |

**Total 2.3 Tests:** 70+ test cases registered

### Test Automation Gap Analysis Result: **NO GAPS FOUND**

| 2.2 Test | 2.3 Equivalent | Status |
|----------|----------------|--------|
| `test_build_stream_job_stage` | `deploy_build` (E001) + build_stream integration | ✅ Covered |
| `test_functional_group_content` | `functional_groups_x86_64` (V011), `functional_groups_aarch64` (V012) | ✅ Covered |
| `test_regctl_registry_images` | `registry_images_x86_64` (V008), `registry_images_aarch64` (V009) | ✅ Covered |
| `test_s3_bucket_images` | `s3_images_x86_64` (V006), `s3_images_aarch64` (V007) | ✅ Covered |
| `test_all_image_packages` | `packages_x86_64` (V018), `packages_aarch64` (V019) | ✅ Covered |

**2.3 Test Enhancements over 2.2:**
1. **Expanded coverage** - 70+ tests vs 10 tests in 2.2
2. **Catalog reuse tests** - 11 tests for dictionary-based image reuse
3. **Naming convention tests** - 5 tests for artifact naming isolation
4. **aarch64 infrastructure tests** - 5 tests for ARM node validation
5. **Cleanup tests** - 11 tests for cleanup verification
6. **Precheck tests** - 5 tests for environment validation
7. **Prepare tests** - 8 tests for infrastructure setup
8. **Security tests** - 2 NFT tests for file permissions

---

# Summary and Recommendations

## Discovery Domain

### Source Code: **NO GAPS**
- 2.3 is a complete superset of 2.2 with enhanced modularity and validation

### Test Automation: **7 GAPS IDENTIFIED**

**Recommended Actions:**

| Priority | Gap | Action |
|----------|-----|--------|
| High | `test_functional_groups_supported` | Add to `fvt/execute/output/test_output.py` |
| High | `test_ip_correlation` | Add to `fvt/execute/output/test_output.py` |
| High | `test_ome_static_groups_match` | Add to new `fvt/execute/ome/test_ome_validation.py` |
| High | `test_admin_mac_validation` | Add to new `fvt/execute/ome/test_ome_validation.py` |
| Medium | `test_parent_service_tag` | Add to `fvt/execute/output/test_output.py` |
| Medium | `test_ome_unassigned_devices` | Add to new `fvt/execute/ome/test_ome_validation.py` |
| Medium | `test_ib_nic_name_validation` | Add to new `fvt/execute/ome/test_ome_validation.py` |

**Estimated Effort:** 8 hours (as per task estimate)

## Image Build Manager Domain

### Source Code: **NO GAPS**
- 2.3 consolidates x86_64 and aarch64 into unified domain with enhanced features

### Test Automation: **NO GAPS**
- 2.3 provides 70+ tests covering all 2.2 functionality plus extensive new coverage

---

# Appendix: File Counts

| Domain | 2.2 Source Files | 2.3 Source Files | 2.2 Test Files | 2.3 Test Files |
|--------|------------------|------------------|----------------|----------------|
| Discovery | 10 | 68 | 1 (9 tests) | 43 (29+ tests) |
| Image Build Manager | 34 (x86_64 + aarch64) | 97 | 2 (10 tests) | 90 (70+ tests) |

---

*Report generated by Devin AI*

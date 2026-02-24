# Discovery Validation Flow Reference

## **Complete Flow Chart with File References**

| **Phase & Task** | **YAML Files Referenced** | **Variable Files Called** | **Key Variables Used** |
|---|---|---|---|
| **Phase 1: Credential Setup** | | | |
| 1. Load sensitive credentials | `discovery_validations/tasks/main.yml` (lines 16-21) | `omnia_config_credentials.yml` (via hostvars) | `provision_password`, `bmc_username`, `bmc_password` |
| **Phase 2: File Existence Validation** | | | |
| 2. Check all 9 config files | `discovery_validations/tasks/include_inputs.yml` | `discovery_validations/vars/main.yml` | `discovery_inputs`, `input_project_dir` |
| 3. Validate software config | `discovery_validations/tasks/include_software_config.yml` | `discovery_validations/vars/main.yml` | `software_config_file`, `input_project_dir` |
| 4. Confirm discovery mechanism | `discovery_validations/tasks/validate_mapping_mechanism.yml` | `discovery_validations/vars/main.yml` | `discovery_mechanism` |
| **Phase 3: Mapping File Validation** | | | |
| 5. Validate PXE mapping file | `discovery_validations/tasks/validate_mapping_file.yml` | `discovery_validations/vars/main.yml` | `mapping_file_path`, `read_mapping_file` |
| 6. Check required fields | `discovery_validations/tasks/validate_mapping_file.yml` | (same as above) | `read_mapping_file.dict` |
| 7. Validate MAC/IP formats | `discovery_validations/tasks/validate_mapping_file.yml` | (same as above) | `read_mapping_file.dict` |
| 8. Update /etc/hosts | `discovery_validations/tasks/update_hosts.yml` | (no vars file) | `read_mapping_file.dict` |
| **Phase 4: Service-Specific Validation** | | | |
| 9. Validate telemetry config | `discovery_validations/tasks/validate_telemetry_config.yml` | `discovery_validations/vars/main.yml` | `telemetry_config`, `idrac_telemetry_support`, `ldms_support` |
| 10. Check iDRAC settings | `discovery_validations/tasks/validate_telemetry_config.yml` | (same as above) | `telemetry_config.idrac_telemetry` |
| 11. Validate LDMS settings | `discovery_validations/tasks/validate_telemetry_config.yml` | (same as above) | `telemetry_config.ldms` |

---

## **Detailed File and Variable Reference Map**

### **Phase 1: Credential Setup**

#### **Task 1: Load Sensitive Credentials**
```yaml
# File: discovery/roles/discovery_validations/tasks/main.yml (lines 16-21)
- name: Set_fact for omnia_config_credentials.yml variables
  ansible.builtin.set_fact:
    provision_password: "{{ hostvars['localhost']['provision_password'] }}"
    bmc_username: "{{ hostvars['localhost']['bmc_username'] }}"
    bmc_password: "{{ hostvars['localhost']['bmc_password'] }}"
  no_log: true
```

**Files Referenced:**
- **Input**: `omnia_config_credentials.yml` (via hostvars from include_input_dir)
- **Task**: `discovery_validations/tasks/main.yml`

**Variable Files Called:**
- **Source**: `omnia_config_credentials.yml` (loaded by include_input_dir role)
- **Target**: Creates hostvars in memory

**Key Variables:**
```yaml
# From omnia_config_credentials.yml
provision_password: "secret_password"
bmc_username: "admin"  
bmc_password: "bmc_secret"
```

---

### **Phase 2: File Existence Validation**

#### **Task 2: Check All Configuration Files**
```yaml
# File: discovery/roles/discovery_validations/tasks/main.yml (lines 23-25)
- name: Include discovery inputs
  ansible.builtin.include_tasks: include_inputs.yml
  with_items: "{{ discovery_inputs }}"
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/include_inputs.yml`
- **Vars**: `discovery_validations/vars/main.yml`

**Variable Files Called:**
```yaml
# File: discovery/roles/discovery_validations/vars/main.yml
discovery_inputs:
  - "omnia_config.yml"
  - "network_spec.yml"
  - "storage_config.yml"
  - "telemetry_config.yml"
  - "security_config.yml"
  - "high_availability_config.yml"
  - "local_repo_config.yml"
  - "user_registry_credential.yml"
  - "provision_config.yml"

input_project_dir: "{{ hostvars['localhost']['input_project_dir'] }}"
```

**Key Variables:**
```yaml
# From vars/main.yml
discovery_inputs: ["omnia_config.yml", "network_spec.yml", ...]
input_project_dir: "/opt/omnia/input/project_default"
```

**Files Checked:**
- `{{ input_project_dir }}/omnia_config.yml`
- `{{ input_project_dir }}/network_spec.yml`
- `{{ input_project_dir }}/storage_config.yml`
- `{{ input_project_dir }}/telemetry_config.yml`
- `{{ input_project_dir }}/security_config.yml`
- `{{ input_project_dir }}/high_availability_config.yml`
- `{{ input_project_dir }}/local_repo_config.yml`
- `{{ input_project_dir }}/user_registry_credential.yml`
- `{{ input_project_dir }}/provision_config.yml`

#### **Task 3: Validate Software Config**
```yaml
# File: discovery/roles/discovery_validations/tasks/main.yml (lines 27-28)
- name: Include software config
  ansible.builtin.include_tasks: include_software_config.yml
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/include_software_config.yml`
- **Vars**: `discovery_validations/vars/main.yml`
- **Config**: `software_config.json`

**Variable Files Called:**
```yaml
# From vars/main.yml
software_config_file: "{{ input_project_dir }}/software_config.json"
```

**Key Variables:**
```yaml
software_config_file: "/opt/omnia/input/project_default/software_config.json"
```

#### **Task 4: Confirm Discovery Mechanism**
```yaml
# File: discovery/roles/discovery_validations/tasks/main.yml (lines 30-31)
- name: Check if discovery mechanism is mapping
  ansible.builtin.include_tasks: validate_mapping_mechanism.yml
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/validate_mapping_mechanism.yml`
- **Vars**: `discovery_validations/vars/main.yml`

**Variable Files Called:**
```yaml
# From vars/main.yml
discovery_mechanism: "mapping"
```

**Key Variables:**
```yaml
discovery_mechanism: "mapping"
# Output: mapping_file_status: true
```

---

### **Phase 3: Mapping File Validation**

#### **Task 5: Validate PXE Mapping File**
```yaml
# File: discovery/roles/discovery_validations/tasks/main.yml (lines 33-35)
- name: Validate mapping file
  ansible.builtin.include_tasks: validate_mapping_file.yml
  when: mapping_file_status
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/validate_mapping_file.yml`
- **Vars**: `discovery_validations/vars/main.yml`
- **Config**: `pxe_mapping_file.csv`

**Variable Files Called:**
```yaml
# From vars/main.yml
mapping_file_path: "{{ input_project_dir }}/pxe_mapping_file.csv"
```

**Key Variables:**
```yaml
mapping_file_path: "/opt/omnia/input/project_default/pxe_mapping_file.csv"
read_mapping_file: {dict: {...}}  # From include_input_dir
mapping_file_status: true  # From previous task
```

#### **Tasks 6-7: Check Fields and Formats**
```yaml
# File: discovery/roles/discovery_validations/tasks/validate_mapping_file.yml
# (Multiple validation tasks within this file)
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/validate_mapping_file.yml`
- **Config**: `pxe_mapping_file.csv` (via read_mapping_file)

**Key Variables:**
```yaml
read_mapping_file:
  dict:
    compute-01:
      functional_group_name: "slurm_node"
      service_tag: "ABC123"
      hostname: "compute-01"
      admin_mac: "00:11:22:33:44:55"
      admin_ip: "172.16.107.201"
      bmc_mac: "AA:BB:CC:DD:EE:FF"
      bmc_ip: "172.16.108.201"
```

#### **Task 8: Update /etc/hosts**
```yaml
# File: discovery/roles/discovery_validations/tasks/main.yml (lines 37-38)
- name: Update hosts file
  ansible.builtin.include_tasks: update_hosts.yml
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/update_hosts.yml`
- **System**: `/etc/hosts` (modified directly)

**Key Variables:**
```yaml
read_mapping_file: {dict: {...}}  # From include_input_dir
```

---

### **Phase 4: Service-Specific Validation**

#### **Task 9: Validate Telemetry Config**
```yaml
# File: discovery/roles/discovery_validations/tasks/main.yml (lines 40-44)
- name: Validate telemetry config
  ansible.builtin.include_tasks: validate_telemetry_config.yml
  when:
    - idrac_telemetry_support | lower == 'true' | default('false') or
      ldms_support | default('false')
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/validate_telemetry_config.yml`
- **Vars**: `discovery_validations/vars/main.yml`
- **Config**: `telemetry_config.yml`

**Variable Files Called:**
```yaml
# From vars/main.yml
idrac_telemetry_support: "{{ telemetry_config.idrac_telemetry.enabled | default(false) }}"
ldms_support: "{{ telemetry_config.ldms.enabled | default(false) }}"
```

**Key Variables:**
```yaml
telemetry_config:  # From include_input_dir
  idrac_telemetry:
    enabled: true
    metrics_interval: 30
  victoria_metrics:
    enabled: true
    retention_days: 30
  ldms:
    enabled: true
    port: 10000

# Computed variables
idrac_telemetry_support: true
ldms_support: true
```

#### **Tasks 10-11: Check iDRAC and LDMS**
```yaml
# File: discovery/roles/discovery_validations/tasks/validate_telemetry_config.yml
# (Multiple validation tasks within this file)
```

**Files Referenced:**
- **Task**: `discovery_validations/tasks/validate_telemetry_config.yml`
- **Config**: `telemetry_config.yml` (via telemetry_config variable)

**Key Variables:**
```yaml
telemetry_config.idrac_telemetry.enabled: true
telemetry_config.idrac_telemetry.metrics_interval: 30
telemetry_config.ldms.enabled: true
telemetry_config.ldms.port: 10000
```

---

## **Quick Reference for Changes**

### **To Modify File List:**
```yaml
# Edit: discovery/roles/discovery_validations/vars/main.yml
discovery_inputs:
  - "omnia_config.yml"
  - "network_spec.yml"
  # Add/remove files here
```

### **To Change File Paths:**
```yaml
# Edit: discovery/roles/discovery_validations/vars/main.yml
input_project_dir: "/custom/path/to/input"
software_config_file: "{{ input_project_dir }}/custom_software.json"
mapping_file_path: "{{ input_project_dir }}/custom_mapping.csv"
```

### **To Add New Validations:**
```yaml
# Edit: discovery/roles/discovery_validations/tasks/main.yml
- name: Include custom validation
  ansible.builtin.include_tasks: validate_custom.yml
  when: custom_validation_enabled

# Create: discovery/roles/discovery_validations/tasks/validate_custom.yml
```

### **To Modify Telemetry Checks:**
```yaml
# Edit: discovery/roles/discovery_validations/vars/main.yml
idrac_telemetry_support: "{{ telemetry_config.custom_telemetry.enabled | default(false) }}"

# Edit: discovery/roles/discovery_validations/tasks/validate_telemetry_config.yml
# Add validation for custom_telemetry
```

---

## **File Structure Summary**

```
discovery/roles/discovery_validations/
├── tasks/
│   ├── main.yml                    # Main orchestration
│   ├── include_inputs.yml          # File existence checks
│   ├── include_software_config.yml # Software validation
│   ├── validate_mapping_mechanism.yml # Discovery mechanism
│   ├── validate_mapping_file.yml   # PXE mapping validation
│   ├── update_hosts.yml           # /etc/hosts update
│   └── validate_telemetry_config.yml # Telemetry validation
├── vars/
│   └── main.yml                    # All variable definitions
└── README.md                       # Documentation
```

**Input Files Referenced:**
```
/opt/omnia/input/project_default/
├── omnia_config.yml
├── network_spec.yml
├── storage_config.yml
├── software_config.json
├── telemetry_config.yml
├── security_config.yml
├── high_availability_config.yml
├── local_repo_config.yml
├── user_registry_credential.yml
├── provision_config.yml
├── pxe_mapping_file.csv
└── omnia_config_credentials.yml
```

---

## **Variable Dependency Summary**

### **Input Variables (from include_input_dir role):**
```yaml
# Configuration data
omnia_config: {...}
network_spec: {...}
storage_config: {...}
software_config: {...}
telemetry_config: {...}
security_config: {...}
ha_config: {...}
local_repo_config: {...}
user_registry_credential: {...}
provision_config: {...}

# Processed data
read_mapping_file: {dict: {...}}
functional_groups: [{name: "..."}, ...]

# Credentials
provision_password: "secret_password"
bmc_username: "admin"
bmc_password: "bmc_secret"

# Paths
input_project_dir: "/opt/omnia/input/project_default"
```

### **Internal Variables (from discovery_validations vars):**
```yaml
# File lists
discovery_inputs:
  - "omnia_config.yml"
  - "network_spec.yml"
  - "storage_config.yml"
  - "telemetry_config.yml"
  - "security_config.yml"
  - "high_availability_config.yml"
  - "local_repo_config.yml"
  - "user_registry_credential.yml"
  - "provision_config.yml"

# File paths
software_config_file: "{{ input_project_dir }}/software_config.json"
mapping_file_path: "{{ input_project_dir }}/pxe_mapping_file.csv"

# Settings
discovery_mechanism: "mapping"

# Computed flags
mapping_file_status: true
idrac_telemetry_support: "{{ telemetry_config.idrac_telemetry.enabled | default(false) }}"
ldms_support: "{{ telemetry_config.ldms.enabled | default(false) }}"
```

### **Output Variables (created by validation):**
```yaml
# Status flags
mapping_file_status: true
config_file_status: true
software_config_status: true

# Updated system files
/etc/hosts: Updated with node entries
```

---

*This reference document provides a complete mapping of the discovery validation flow, making it easy to locate files, understand variable dependencies, and make modifications quickly.*

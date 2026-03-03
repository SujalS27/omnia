#!/bin/bash
# Script to fix oim_timezone in all template files

cd /omnia/sujal/omnia/discovery/roles/openchami_cloud_init/templates/cloud_init

for file in *.yaml.j2; do
    if grep -q "hostvars\['oim'\]\['oim_timezone'\]" "$file"; then
        sed -i "s/hostvars\['oim'\]\['oim_timezone'\]/hostvars['oim']['oim_timezone'] | default('UTC')/g" "$file"
        echo "Fixed $file"
    fi
done

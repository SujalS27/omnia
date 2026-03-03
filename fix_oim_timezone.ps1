# Script to fix oim_timezone in all template files
Get-ChildItem "discovery\roles\openchami_cloud_init\templates\cloud_init\*.yaml.j2" | ForEach-Object {
    $content = Get-Content $_.FullName
    if ($content -match "hostvars\['oim'\]\['oim_timezone'\]") {
        $content = $content -replace "hostvars\['oim'\]\['oim_timezone'\]", "hostvars['oim']['oim_timezone'] | default('UTC')"
        Set-Content $_.FullName $content
        Write-Host "Fixed $($_.Name)"
    }
}

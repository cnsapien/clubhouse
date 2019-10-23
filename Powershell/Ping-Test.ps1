#------------------------------------------------------------------------------ 
# 
# Copyright © 2012 Microsoft Corporation.  All rights reserved. 
# 
# THIS CODE AND ANY ASSOCIATED INFORMATION ARE PROVIDED “AS IS” WITHOUT 
# WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT 
# LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY AND/OR FITNESS 
# FOR A PARTICULAR PURPOSE. THE ENTIRE RISK OF USE, INABILITY TO USE, OR  
# RESULTS FROM THE USE OF THIS CODE REMAINS WITH THE USER. 
# 
#------------------------------------------------------------------------------ 
# 
# PowerShell Source Code 
# 
# NAME: 
#    Ping-Test.ps1 
# 
# VERSION: 
#    1.0 
# 
#------------------------------------------------------------------------------ 

#NOTE: Be sure to populate the $Computers array with valid host names

param(
    [String] $FolderPath = 'C:\ConnectionLogs',
    [Int32] $HoursToRun = 24,
    [System.Array] $Computers = ('ADFS01','ADFS02','ADFS03','ADFS04'),
)

if (-not (Test-Path -Path $FolderPath)) { New-Item -ItemType Directory -Path $FolderPath }

$ScriptStartTime = Get-Date
$FirstRun = $true

while ((Get-Date) -lt $ScriptStartTime.AddHours($HoursToRun)) {
    foreach ($Computer in $Computers) {
        ## ICMP Pings
        $Output = $null
        $PingTime = (Get-Date).ToString('G')
        
        $Headers = "Address,StartTime,Duration,Error,Output"

        if ($FirstRun) {
            $Headers | Set-Content -Path ('{0}\{1}_ICMPPings.csv' -f $FolderPath,$Computer)
        }

        $PingOutput = (((ping -n 1 -w 5000 $Computer | Out-String).Trim()) -replace '\n','--')
        $Success = $PingOutput -match 'time\=(\d*)ms'
        $PingMS = if ($Success) {$Matches[1]} else {$null}
        # $Output = Test-Connection -ComputerName $Computer -Count 1 -ErrorAction SilentlyContinue | Select-Object -Property Address,IPV4Address,ResponseTime,@{Label='StartTime';Expression={$PingTime}} | ConvertTo-Csv -NoTypeInformation | Select-Object -Last 1
        # $Output | Add-Content -Path ('{0}\{1}_ICMPPings.csv' -f $FolderPath,$Computer)
        
        $Output2 = New-Object -TypeName PSObject -Property @{
            Address = $Computer
            StartTime = $PingTime
            Duration = $PingMS
            Error = if ($LASTEXITCODE -ne 0) { 'True' } else { 'False' }
            Output = $PingOutput
        } | Select-Object Address,StartTime,Duration,Error,Output
        
        $Output2 | ConvertTo-Csv -NoTypeInformation | Select-Object -Last 1 | Add-Content -Path ('{0}\{1}_ICMPPings.csv' -f $FolderPath,$Computer)
        
    }
    $FirstRun = $false
    Start-Sleep -Seconds 1
}
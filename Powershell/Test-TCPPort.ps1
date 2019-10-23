# Test-TCPPort.ps1
# Written by Bill Stewart

#requires -version 2

<#
.SYNOPSIS
Tests whether TCP host(s) are listening on a particular port.

.DESCRIPTION
Tests whether TCP host(s) are listening on a particular port.

.PARAMETER HostName
Specifies one or more host names and/or IP addresses. Wildcards are not permitted. The default is the current computer.

.PARAMETER Port
Specifies one or more port numbers to test. The default port is 443 (HTTPS).

.PARAMETER Timeout
Specifies the timeout, in milliseconds, to wait for a response. The default is 3000 (3 seconds).

.OUTPUTS
Objects with the following properies:
  HostName - The specified host name/IP address
  Port - Port number
  Timeout - Timeout (milliseconds)
  Result - $true if host responded within the timeout, or $false otherwise
#>

[CmdletBinding()]
param(
  [Parameter(ValueFromPipeline = $true)]
  [ValidateNotNullOrEmpty()]
  $HostName = [Net.Dns]::GetHostName(),

  [ValidateRange(1,65536)]
  [Int[]] $Port = 443,

  [Int] $Timeout = 3000
)

begin {
  function Test-TCPPort {
    param(
      [String] $hostName,

      [Int] $port,

      [Int] $timeout
    )
    $outputObject = "" | Select-Object `
      @{Name = "HostName"; Expression = {$hostName}},
      @{Name = "Port";     Expression = {$port}},
      @{Name = "Timeout";  Expression = {$timeout}},
      @{Name = "Result";   Expression = {$false}}
    $tcpClient = New-Object Net.Sockets.TcpClient
    $asyncResult = $tcpClient.BeginConnect($hostName,$port,$null,$null)
    $waitHandle = $asyncResult.AsyncWaitHandle.WaitOne($timeout,$false)
    if ( $waitHandle ) {
      try {
        $tcpClient.EndConnect($asyncResult)
        $tcpClient.Close()
        $outputObject.Result = $true
      }
      catch [Management.Automation.MethodInvocationException] {
      }
    }
    $outputObject
  }
}

process {
  foreach ( $HostNameItem in $HostName ) {
    foreach ( $PortItem in $Port ) {
      Test-TCPPort $HostNameItem $PortItem $Timeout
    }
  }
}

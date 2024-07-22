# Begin download commands
$scriptName = 'createSMBView'
$repoURL = 'https://raw.githubusercontent.com/cohesity/community-automation-samples/main/powershell'
(Invoke-WebRequest -UseBasicParsing -Uri "$repoUrl/$scriptName/$scriptName.ps1").content | Out-File "$scriptName.ps1"; (Get-Content "$scriptName.ps1") | Set-Content "$scriptName.ps1"
(Invoke-WebRequest -UseBasicParsing -Uri "$repoUrl/cohesity-api/cohesity-api.ps1").content | Out-File cohesity-api.ps1; (Get-Content cohesity-api.ps1) | Set-Content cohesity-api.ps1
# End download commands

$ViewNameNew = read-host "What is the view name?"
$VIPNAME = "cohesity-01"
./createSMBView.ps1 -vip $VIPNAME -username admin -viewName $ViewNameNew

$PSPAth = "\\cohesity-01\" + $ViewNameNew
new-PSDrive -Name "X" -Root $PSPath -Persist -PSProvider "FileSystem"

$FileCount= read-host "How many files do you want created?"
$filename1 = read-host "File Name?"
$fileext = Read-Host "File Extension"
#$path = read-host "Where do you want the files created"


for ($num = 1;$num -le $FileCount ;$num++){
$filename = $filename1 + $num
$fullpath = "X:\" + $filename + "." + $fileext
Write-Host $fullpath
$file = [io.file]::Create($fullpath)
$file.SetLength(100gb)
$file.Close()
Get-Item $fullpath
}

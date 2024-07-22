$FileCount= read-host "How many files do you want created?"
$filename1 = read-host "File Name?"
$fileext = Read-Host "File Extension"
$path = read-host "Where do you want the files created"


for ($num = 1;$num -le $FileCount ;$num++){
$filename = $filename1 + $num
$fullpath = $path + "\" + $filename + "." + $fileext
Write-Host $fullpath
$file = [io.file]::Create($fullpath)
$file.SetLength(100gb)
$file.Close()
Get-Item $fullpath
}
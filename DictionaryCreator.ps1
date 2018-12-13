#This Script retrieves project's web.config from TFS and extracts placeholders
#Then, script connects to each environment (INT,UAT and PROD)and finds the corresponding key in the actual web.config file
#Output is a text file
# ex. output
#->ConnectionString_Server localhost
#->ConnectionString_Database mydb
#->ConnectionString_UID root


. "C:\Scripts\Get-Web-Config-Info.ps1" 

clear-host
$rules=$False
$WebConfigPlaceholder="c:\Scripts\webPlaceholder.config"
$RUsernameProd = 'xxx'
$RPasswordProd = 'yyy'
$RUsernameUat = 'xxx'
$RPasswordUat = 'yyy'
$RUsernameInt = 'xxx'
$RPasswordInt = 'yyy'
$GITUserName='xxx'
$GITPassword='yyy'
$temppath = "C:\Scripts\GIT_TEMP"
$OutputFileLocation="C:\libraries\"
$ACIListLocation="C:\Scripts\ACIList.txt"
$Results="C:\Scripts\Result.txt"
$Report = @()



function Log-write([string]$LogText, $color='White') {
	Add-Content $Results  $("$(Get-Date -Format G) $LogText")
	write-host $("$(Get-Date -Format G) $LogText") -ForegroundColor $color
	}


function Get-Data([string]$username, [string]$password, [string]$url, [string]$ACI) {
	$credPair = "$($username):$($password)"
	$encodedCredentials = [System.Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes($credPair))
	$headers = @{ Authorization = "Basic $encodedCredentials" }
	$responseData = Invoke-WebRequest -Uri $url -Method POST -Headers $headers  -ContentType "application/json"  -Body "{'code': '$ACI'}" -UseBasicParsing
	return $responseData
	}

function cleanFiles() {
	if( (Test-Path -Path $temppath ) ){
		Log-write $("Deleting: $temppath")
		Remove-Item -Path $temppath  -Force -Recurse
	}

	if( (Test-Path -Path $WebConfigPlaceholder ) ){
		Log-write $("Deleting: $WebConfigPlaceholder")
		Remove-Item -Path $WebConfigPlaceholder  -Force -Recurse
	}

	if( (Test-Path -Path $OutputFileLocation"DICT_"$ACI"-*" ) ){
		Log-write $("Deleting: $OutputFileLocation DICT_$ACI-*")
		Remove-Item -Path $OutputFileLocation"DICT_"$ACI"-*"   -Force
	}	

	}

function Copy-Config-Placeholder([string]$GITUserName, [string]$GITPassword, [string]$temppath, [string]$webconfiglocal, [string]$ProjectName, [string]$PackageName, [string]$DeploymentType) {
	New-Item -ItemType directory -Path $temppath
	Set-Location -Path $temppath
	Log-write $("https\://$GITUserName\:$GITPassword@scoretfs.isbank/ISBANK/$ProjectName/_git/$PackageName")
	git -c http.sslVerify=false clone --single-branch -b develop https://$($GITUserName):$($GITPassword)@scoretfs.isbank/ISBANK/$($ProjectName)/_git/$($PackageName)
	if ($DeploymentType -eq "web"){
		$webconfigdestination = Get-Childitem -Path $temppath -Include web.config -Recurse
		[int]$occurrences = 666
		if ($webconfigdestination -is [array]){
			for ($i=0; $i -le $webconfigdestination.GetUpperBound(0); $i++){
				$count = $webconfigdestination[$i].toString().Split("\").GetUpperBound(0)
				if ( $occurrences -gt $count){
					$occurrences = $count
					$index=$i
				}
			}	
		$webconfig = $webconfigdestination[$index] 
		}
		else {
			$webconfig = $webconfigdestination
		}
		Move-Item -Path $webconfig -Destination $webconfiglocal -Force
		Set-Location -Path C:\Scripts
		return
	}
	elseif ($DeploymentType -eq "windowsService"){
		Log-write $("TEMP PATH $temppath")
		$webconfigdestination = Get-Childitem -Path $temppath -Include "app.config" -Recurse
		Log-write $("webconfigdestination $webconfigdestination")		
		$webconfig = $webconfigdestination
		Move-Item -Path $webconfig -Destination $webconfiglocal -Force
		Set-Location -Path C:\Scripts
		return
		}
	}

function Get-Server-Path([object]$dataToDict,[string]$env) {
	$index="666"
	for ($i=0; $i -lt $dataToDict.iisinfo.length; $i++) {
		[string]$currentenv=$dataToDict.iisinfo[$i].env.trim()
		if ($currentenv -eq $env){
            $index = $i
			}
	}
	if ($index -eq "666") {
		return
	}
	$Rpath = $dataToDict.iisinfo[$index].detail.paths[0]
	return $Rpath
	}

function Get-Project-Package ([object]$dataToDict) {
	$Projectname = $dataToDict.iisinfo[0].detail.name
	$Packagename = $dataToDict.package.name
	Log-write $("package$dataToDict.package.name")
	return $Projectname, $Packagename
	}
	
function Get-Deployment-Type ([object]$dataToDict) {
	for ($i=0; $i -lt $dataToDict.iisinfo.length; $i++) {
		[string]$currentenv=$dataToDict.iisinfo[$i].env.trim()
		if ($currentenv -eq "prod"){
            $indexprod = $i
			}
		elseif ($currentenv -eq "uat"){
			$indexuat = $i
			}
		elseif ($currentenv -eq "int"){
			$indexint = $i
			}
	}
	$DeploymentType = $dataToDict.iisinfo[$indexprod].detail.paths[0]
	$DeploymentType = $DeploymentType.split('\\')[4]
	$httpBinding = $dataToDict.iisinfo[$indexprod].webSiteInfo.httpBinding
	$httpsBinding = $dataToDict.iisinfo[$indexprod].webSiteInfo.httpsBinding
	$siteName = $dataToDict.iisinfo[$indexprod].webSiteInfo.siteName
	$SSL=$False
	if ($httpsBinding){
		$SSL=$True
		$ProdBinding=$httpsBinding
		if ($dataToDict.iisinfo[$indexuat].webSiteInfo.httpsBinding -ne ""){
			$UatBinding=$dataToDict.iisinfo[$indexuat].webSiteInfo.httpsBinding
		}
		else{
			$UatBinding=$dataToDict.iisinfo[$indexuat].webSiteInfo.httpBinding
		}
		$IntBinding=$dataToDict.iisinfo[$indexint].webSiteInfo.httpBinding
	}
	else{
		$SSL=$False
		$ProdBinding=""
		$UatBinding=""
		$IntBinding=""
	}


	if ($DeploymentType.ToLowerInvariant() -eq "windowsservices"){
		return "WindowsService",$SSL,$ProdBinding,$UatBinding,$IntBinding,$siteName
	}
	else{
		return "Web",$SSL,$ProdBinding,$UatBinding,$IntBinding,$siteName
	}	
}


$ACIListConfig = Get-Content -Path $ACIListLocation	


Log-write $("------------------$ACI---$ProjectName--$PackageName---------------")

foreach ($ACI in $ACIListConfig ){
	cleanFiles
	Log-write $("ACI: $ACI")
	Log-write "Getting Data from Genome Server"
	Log-write ""
	Log-write ""
	$data = Get-Data -username xxx -password yyy -url https://genom.isbank/eamintegration/api/package -ACI $ACI
	$dataToDict = $data | ConvertFrom-Json
	$ProjectName, $PackageName = Get-Project-Package -dataToDict $dataToDict
	Log-write $("ProjectName: $ProjectName")
	Log-write $("PackageName: $PackageName")
	$DeploymentType,$SSL,$ProdBinding,$UatBinding,$IntBinding,$siteName = Get-Deployment-Type -dataToDict $dataToDict
	Log-write $("Deployment Type: $DeploymentType")


	Log-write $("Copying $DeploymentType Config From GIT")
	Copy-Config-Placeholder -GITUserName $GITUserName -GITPassword $GITPassword -temppath $temppath -webconfiglocal $WebConfigPlaceholder -ProjectName $ProjectName -PackageName $PackageName -DeploymentType $DeploymentType 
	if( -Not (Test-Path -Path $WebConfigPlaceholder ) ){
		Log-write "Cannot Retrieve WebConfig From GIT"
		Continue
	}	
	$LocalWebConfig = Get-Content -Path $WebConfigPlaceholder	
	Log-write "FOR REFERENCE"
	Log-write ""
	Log-write $("$environment Config With PlaceHolder")
	Log-write ""
	Log-write ""

	foreach ($line in $LocalWebConfig )	{
		Log-write $line -color Yellow
	}

	foreach ($environment in ("int","uat","prod")){
		$Output = @()
		$keymissingvalue = @()
		$Rpath = Get-Server-Path -dataToDict $dataToDict -env $environment
		Log-write $("Preparing Dictionary for $($environment.ToUpperInvariant()) environment")
		Log-write $("	Remote Server Path: $Rpath")
		Log-write $("	Project Name: $ProjectName")
		Log-write $("	Package Name: $PackageName")
		Log-write ""
		Log-write ""
		if ($environment -eq "int") {
			$RUsername = $RUsernameInt
			$RPassword = ConvertTo-SecureString -AsPlainText $RPasswordInt -Force
			$RCred = New-Object System.Management.Automation.PSCredential -ArgumentList $RUsername,$RPassword
		}
		elseif ($environment -eq "uat") {
			$RUsername = $RUsernameUat
			$RPassword = ConvertTo-SecureString -AsPlainText $RPasswordUat -Force
			$RCred = New-Object System.Management.Automation.PSCredential -ArgumentList $RUsername,$RPassword
		}
		elseif ($environment -eq "prod") {
			$RUsername = $RUsernameProd
			$RPassword = ConvertTo-SecureString -AsPlainText $RPasswordProd -Force
			$RCred = New-Object System.Management.Automation.PSCredential -ArgumentList $RUsername,$RPassword
		}
		Log-write "Connecting to Remote Server"
		Log-write ""
		Log-write ""
		New-PSDrive -Name "DEST" -PSProvider "FileSystem" -Root $Rpath -credential $RCred

		
		if($DeploymentType -eq "web"){
			$RemoteWebConfig = Get-Content -Path "$Rpath\web.config"
			$RemoteWebConfigPath = "$Rpath\web.config"
			Log-write $($RemoteWebConfigPath)
			if( -Not (Test-Path -Path "$Rpath\web.config" ) ){
				Log-write $("Cannot Retrieve WebConfig From Remote Path: $Rpath")
				Log-write $($environment.ToUpperInvariant() + "   FAILED!! Cannot Retrieve WebConfig")
				Continue
			}	
		}	
		elseif($DeploymentType -eq "windowsService"){
			$RemoteWebConfigPath = "$Rpath\$PackageName.exe.config"
			Log-write $("Trying to Retrieve $RemoteWebConfigPath")
			$RemoteWebConfig = Get-Content -Path $RemoteWebConfigPath

			if( -Not (Test-Path -Path $RemoteWebConfigPath)) {
				Log-write $("Cannot Retrieve Config From Remote Path: $RemoteWebConfigPath")
				if ($PackageName.Substring($PackageName.get_Length()-5).ToLowerInvariant() -eq "batch") {
					$RemoteWebConfigPath="$Rpath\$($PackageName.Substring(0,$PackageName.get_Length()-5))"
					$RemoteWebConfigPath="$RemoteWebConfigPath.exe.config"
					Log-write $("Trying to Retrieve from Path :$RemoteWebConfigPath")
					$RemoteWebConfig = Get-Content -Path $RemoteWebConfigPath
				}
			}
				if( -Not (Test-Path -Path $RemoteWebConfigPath)) {
				Log-write "Trying App.Config"
				$RemoteWebConfigPath = "$Rpath\App.config"
				$RemoteWebConfig = Get-Content -Path $RemoteWebConfigPath
				Log-write $($RemoteWebConfigPath)	
			}
				if( -Not (Test-Path -Path $RemoteWebConfigPath)) {
					Log-write "Trying Some Variations"
					$PackageNameVariation=$PackageName.Replace("Service",".Service")
					$RemoteWebConfigPath = "$Rpath\$PackageNameVariation.exe.config"
					$RemoteWebConfig = Get-Content -Path $RemoteWebConfigPath
					Log-write $($RemoteWebConfigPath)
					if( -Not (Test-Path -Path $RemoteWebConfigPath ) ){
						Log-write "Cannot Retrieve WebConfig From Remote Path: $Rpath"
						Log-write $("$($environment.ToUpperInvariant())   FAILED!! Cannot Retrieve WebConfig")
						Continue
					}	
				}
		}		
	
		Log-write "FOR REFERENCE"
		Log-write ""
		Log-write $(" Config In the Live $environment Environment")
		Log-write ""
		Log-write $("WEBREMOTE: $RemoteWebConfigPath")
		foreach ($line in $RemoteWebConfig ){
			Log-write -logtext $line  -color Blue
		}
		$SEL = $LocalWebConfig | Select-String -Pattern '{{'
		Log-write "Finding Values Comparing Two App.config Files"
		Log-write ""
		Log-write ""
		$keycount=0
		$valuecount=0
		write-host("SSL:::$SSL")
		if ($SSL -and $environment -eq "prod"){
			$Output += ,@("Protocol","https")
			$Output += ,@("Port",$ProdBinding.split(":")[1])
			$Output += ,@("CertificateName",$siteName)
			Log-write -Logtext $("SSL Rule - Protocol https") -color Green
			Log-write -Logtext $("SSL Rule - Port $($ProdBinding.split(":")[1])") -color Green
			Log-write -Logtext $("SSL Rule - CertificateName $siteName") -color Green
		}
		if ($SSL -and $environment -eq "uat"){
			if ($ProdBinding.split(":")[1] -eq "80"){
				$Output += ,@("Protocol","http")
				Log-write -Logtext $("SSL Rule - Protocol http") -color Green	
			}
			else{
				$Output += ,@("Protocol","https")	
				Log-write -Logtext $("SSL Rule - Protocol https") -color Green
			}
			$Output += ,@("Port",$ProdBinding.split(":")[1])
			$Output += ,@("CertificateName",$siteName)
			Log-write -Logtext $("SSL Rule - Port $($ProdBinding.split(":")[1])") -color Green
			Log-write -Logtext $("SSL Rule - CertificateName $siteName") -color Green
		}
		if ($SSL -and $environment -eq "int"){
			$Output += ,@("Protocol","http")
			$Output += ,@("Port",$ProdBinding.split(":")[1])
			$Output += ,@("CertificateName",$siteName)
			Log-write -Logtext $("SSL Rule - Protocol http") -color Green
			Log-write -Logtext $("SSL Rule - Port $($ProdBinding.split(":")[1])") -color Green
			Log-write -Logtext $("SSL Rule - CertificateName $siteName") -color Green
		}



		foreach ($line in $SEL){
			$pattern = "{{(.*?)}}"
			$keys = [regex]::Matches($line,$pattern)

			foreach ($key in $keys){
				$key1=$key.groups[1].value
				$keySplit=$key.groups[0].value
				$startString = $line -split $keySplit
				$startString = $startString[0] -split('}}')
				$startString=$startString[-1].split(' ')[-1]
				$endString = $line -split $keySplit
				$endString=$endString[1] -split('{{')
				$endString=$endString[0].split(' ')[0]
				$repeat=$False
				foreach ($Outputkey in $Output){
					if($Outputkey[0] -eq $key1){
						$repeat=$True
					}
				}
				if (-Not $repeat){
				$value, $RuleInfo = Get-Web-Config-Info -RemoteWebConfig $RemoteWebConfig  -RemoteWebConfigPath $RemoteWebConfigPath -key $key1 -startString $startString -endString $endString
				if ($value -eq "!!!!EMPTY!!!!"){
					$keymissingvalue += ,@($key1,"$startString(.*?)$endString")
				}
				else{$valuecount=$valuecount+1}

				$Output += ,@($key1,$value)
				$keycount=$keycount+1
				if ($RuleInfo -ne "rule666"){
					Log-write -Logtext $("$RuleInfo - $key1 $value") -color Green
				}
				Else{
					Log-write -Logtext $("$RuleInfo - $key1 $value") -color Red
				}
			
			}
			}
		}
		$OutputFileLocation1= $OutputFileLocation+"DICT_"+$ACI+"-"+$environment.ToUpperInvariant()+".txt"
		if (Test-Path $OutputFileLocation1){ Remove-Item $OutputFileLocation1 }
			Log-write $("Creating The Output File $OutputFileLocation1")
			Log-write ""
			Log-write ""
			foreach($line in $Output)  {  
				Add-Content -Path $OutputFileLocation1 -Value "$line"
			}  

			if ($keycount -eq $valuecount){
				Log-write -Logtext "    SUCCESS!!" -color Blue
				Log-write $("$($environment.ToUpperInvariant())   SUCCESS")
			}
			else{
				Log-write $("$($environment.ToUpperInvariant())   SUCCESS with Missing Values:")
				Log-write -Logtext "   SUCCESS with Missing Values" -color Yellow
			}
			Log-write $("   Number of Keys$keycount")
			Log-write $("   Number of Values$valuecount")
			Log-write $("   Missing Values:")
			foreach($line in $keymissingvalue)  {  
			Log-write -Logtext $("       $line") -color Red
			}
			Log-write ""
			Log-write ""
			Log-write "Removing Mapped Drive "
			Remove-PSDrive -Name "DEST" -Force
	}
}
#Remove-Item -Path $WebConfigPlaceholder  -Force -Recurse
Log-write "-----------------------------------------------------------------"
Log-write "------------------------ALL DONE!!-------------------------------"
Log-write "-----------------------------------------------------------------"
Log-write ""
Log-write ""
Log-write ""


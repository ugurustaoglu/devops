
#This Script is the Decision Engine to Extract Web.Config Keys based on Placeholders
#Main Script DictionaryCreator

#Rule1: logpath -->C:\Loglar
#Rule2: nodename like key --> name -eq address or value return value
#Rule3: $node.attributes.value[0] -eq $key --> return $node.InnerText
#Rule4: $node.attributes.value[0] -eq $key --> return $node.attributes.value[1]
#Rule5: [regex]::Match($node.attributes.value[$i],$pattern) and only one occurence--> return it
#Rule6: $node.attributes.value -like "*"+$key+"*" and $node.attributes.name[$i] -eq "value"/"address"/"source" --> return $node.attributes.value[$i]
#Rule7: $node.attributes.value -like "*"+$key+"*" --> innertext
#Rule8: $node.attributes.value -like "*"+$keysmall+"*"  and only one occurence--> return it
#Rule9: $node.attributes.value -eq $keysmall and only one occurence--> [regex]::Match($node.attributes.value[$i+1],$pattern).groups[1].value
#Rule10: plain-text [regex]::Match($line,$pattern) and only one occurence--> return it
#Rule11: nodename -eq $keysmall --> [regex]::Match($value,$pattern2(without QuotationMark))
#Rule12: Match($value,$pattern3($startString2(without QuotationMark)(.*?);")) and only one occurence--> return it

function Get-Web-Config-Info([xml]$RemoteWebConfig, [string]$RemoteWebConfigPath, [string]$key,[string]$startString,[string]$endString){
	$RemoteWebConfig2 = Get-Content -Path $RemoteWebConfigPath
	$pattern = "$startString(.*?)$endString"
	$startString2=$startString.split('"')[-1]
	$usernames="username","uid","user","user id","user name","userid","id"
	$passwords="password","pwd","pass"
	$databases="database","dbname","datasource","source","data source"
	$servers="server","servername","server name"
	$keysmall=$key.split('_')[0]
	$keysmall=$keysmall.split('-')[0]
	$keyend=$key.split('_')[-1]
	$pattern2 = "$startString2(.*?)$endString"
	$pattern3 = "$startString2(.*?);"
	$nodes = $RemoteWebConfig.SelectNodes("//*") 
	if ($rules){Log-write $("keyname:: $key")}
	if ($rules){Log-write $("pattern:: $pattern")}

	if ("logpath" -eq $key.ToLowerInvariant()){
		if ($rules){Log-write "rule1"}
		return "C:\Loglar","rule1"
	}

	foreach ($node in $nodes) {
		if ($node.name -like "*"+$key+"*"){
			for ($i=0; $i -lt $node.attributes.name.count; $i++) {
				if ($node.attributes.name.count -eq 1){
					$name = $node.attributes.name
					$value = $node.attributes.value
				}
				else{
					$name = $node.attributes.name[$i]
					$value = $node.attributes.value[$i]
				}
				if ($name -eq 'address'){
					if ($rules){Log-write "rule2 - address"}
					return $value,"rule2"
				}
				if ($name -eq 'value'){
					if ($rules){Log-write "rule2 - value"}
					return $value,"rule2"
				}
			}
		}
	}
	
	foreach ($node in $nodes) {
		if ($node.attributes.value -AND $node.attributes.value[0] -eq $key){
			if ($rules){Log-write "rule3"}
			if ($node.Innertext){
				if ($rules){Log-write $("Inner Text: $node.InnerText")}
				return $node.InnerText,"rule3"
			}
		}
	}

	foreach ($node in $nodes) {
		if ($node.attributes.value -AND $node.attributes.value[0] -eq $key){
			if ($rules){Log-write "rule4"}
			return $node.attributes.value[1],"rule4"
		}
	}
	
	$hitcount=0

	foreach ($node in $nodes) {
		for ($i=0; $i -lt $node.attributes.name.count; $i++) {
			if ($node.attributes.name.count -eq 1){
				$name = $node.attributes.name
				$value = $node.attributes.value
				continue
			}
			else{
				$name = $node.attributes.name[$i]
				$value = $node.attributes.value[$i]
			}
			$nextindex=$i+1
			if ($value -like "*$keysmall*" -and $node.attributes.name.count -ge $nextindex -and $node.attributes.value[$nextindex]){
				if($node.attributes.value[$nextindex].contains(";")){
					$databaseattributes=$node.attributes.value[$nextindex].split(';')
					for ($i=0; $i -lt $databaseattributes.count; $i++){
						$dbconn=$databaseattributes[$i].split('=')
						if($keyend -eq $dbconn[0]){
							$hitcount=$hitcount+1
							$key = $dbconn[1]
						}
						elseif($usernames -contains $keyend -and $usernames -contains $dbconn[0]){
							$hitcount=$hitcount+1
							$key = $dbconn[1]
						}
						elseif($passwords -contains $keyend -and $passwords -contains $dbconn[0]){
							$hitcount=$hitcount+1
							$key = $dbconn[1]
						}
						elseif($databases -contains $keyend -and $databases -contains $dbconn[0]){
							$hitcount=$hitcount+1
							$key = $dbconn[1]
						}
						elseif($servers -contains $keyend -and $servers -contains $dbconn[0]){
							$hitcount=$hitcount+1
							$key = $dbconn[1]
						}
					}

				}
			}
		}
		
	}

	if ($hitcount -eq 1){
		if ($rules){Log-write "rule5"}
		return $key,"rule5"
	}
	


	foreach ($node in $nodes) {
		if ($node.attributes.value -like "*"+$key+"*"){



			for ($i=0; $i -lt $node.attributes.name.count; $i++) {
				if ($node.attributes.name.count -eq 1){
					$name = $node.attributes.name
					$value = $node.attributes.value
				}
				else{
					$name = $node.attributes.name[$i]
					$value = $node.attributes.value[$i]
				}			
				if ($name -eq "value") {
					if ($rules){Log-write "rule6 - value"}
					return $value,"rule6"
				}
				elseif ($name -eq "address") {
					if ($rules){Log-write "rule6 - address"}
					return $value,"rule6"
				}
				elseif ($value -like "*Source*") {
					if ($rules){Log-write "rule6 - Source"}
					return $value,"rule6"
				}
			}

		}
	}

	foreach ($node in $nodes) {
		if ($node.attributes.value -like "*"+$key+"*"){
			if ($node.Innertext){
				if ($rules){Log-write "rule7"}
				if ($rules){Log-write $("Inner Text: $node.InnerText")}
				return $node.InnerText,"rule7"
			}
		}
	}
	
	$hitcount=0
	foreach ($node in $nodes) {
		if ($node.attributes.value -like "*"+$keysmall+"*"){
			for ($i=0; $i -lt $node.attributes.name.count; $i++) {
				if ($node.attributes.name.count -eq 1){
					$name = $node.attributes.name
					$value = $node.attributes.value
				}
				else{
					$name = $node.attributes.name[$i]
					$value = $node.attributes.value[$i]
				}				

				if ([regex]::Match($value,$pattern).groups[1].value -ne "") {				
					$key = [regex]::Match($value,$pattern).groups[1].value
					$hitcount=$hitcount+1
#					$key = $key.split(';')[0]
				}
			}
		}
		if ($hitcount -eq 1){
			if ($rules){Log-write "rule8"}
			return $key,"rule8"
		}
	}


	$hitcount=0
	foreach ($node in $nodes) {
		if ($node.attributes.value -eq $keysmall){
			for ($i=0; $i -lt $node.attributes.name.count-1; $i++) {
				if ($node.attributes.name.count -eq 1){
					$name = $node.attributes.name
					$value = $node.attributes.value
				}
				else{
					$name = $node.attributes.name[$i+1]
					$value = $node.attributes.value[$i+1]
				}	


				if ([regex]::Match($value,$pattern).groups[1].value -ne "") {				
					$key = [regex]::Match($value,$pattern).groups[1].value
#					$key = $key.split(';')[0]
					$hitcount=$hitcount+1
				}
			}
		}
	}
	if ($hitcount -eq 1){
		if ($rules){Log-write "rule9"}
		return $key,"rule9"
	}
	
	$hitcount=0
	foreach ($line in $RemoteWebConfig2) {
		if ([regex]::Match($line,$pattern).groups[1].value -ne ""){
			$key = [regex]::Match($line,$pattern).groups[1].value
			$hitcount=$hitcount+1
#			$key = $key.split(';')[0]
		}
	}
	if ($hitcount -eq 1){
		if ($rules){Log-write "rule10"}
		return $key,"rule10"
	}

	foreach ($node in $nodes) {
		if ($node.name -eq $keysmall){
			for ($i=0; $i -lt $node.attributes.name.count; $i++) {
				if ($node.attributes.name.count -eq 1){
					$name = $node.attributes.name
					$value = $node.attributes.value
				}
				else{
					$name = $node.attributes.name[$i]
					$value = $node.attributes.value[$i]
				}	

				if ([regex]::Match($value,$pattern2).groups[1].value -ne ""){
				$key = [regex]::Match($value,$pattern2).groups[1].value
				if ($rules){Log-write "rule11"}
				return $key,"rule11"
				}
			}
		}
	}

	$hitcount=0
	foreach ($node in $nodes) {
		for ($i=0; $i -lt $node.attributes.name.count; $i++) {
			if ($node.attributes.name.count -eq 1){
				$name = $node.attributes.name
				$value = $node.attributes.value
			}
			else{
				$name = $node.attributes.name[$i]
				$value = $node.attributes.value[$i]
			}
			if ($value -ne $null ){

				$value1=$value.ToLowerInvariant()
				$value2=$pattern.ToLowerInvariant()
				$comparison =""
				if ($value1 -ne $null -AND $value2 -ne $null){
					$value1=$value1.ToLowerInvariant()
					$comparison = [regex]::Match($value1,$value2).groups[1].value
				}
				if ($comparison -ne "") {				
					$key = [regex]::Match($value1,$value2).groups[1].value
					$key = $value.SubString($value1.IndexOf($key),$key.tostring().length)
					$hitcount=$hitcount+1
#				$key = $key.split(';')[0]
				}
			}
		}
	}	
	if ($hitcount -eq 1){
		if ($rules){Log-write "rule12"}
		return $key,"rule12"
	}

	return "!!!!EMPTY!!!!","rule666"
}

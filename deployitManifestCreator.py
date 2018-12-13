#This script generates deployit-manifest.xml file based on the architecture model.
#There are two main types: .NET and Java
#For .NET Script gets data from webservice, parses the data(json), fills the xml and sends the resulting XML to the developer
#For Java, it downloads the Project from local repository, extracts and parses POM.XML for necessary fields and sends the resulting XML to the developer

# -*- coding: latin5
import requests
import json
from pprint import pprint
import socket
import ftplib
from ftplib import FTP
from subprocess import call
import zipfile
import os, sys, shutil,re
import xml.etree.ElementTree as ET
import smtplib
import connectdb
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import ntpath

#ACI = 'ACI09839'
GITUserName = "xxx"
GITPassword = "yyy"
port=21
ip="10.80.20.30"
FTPUserName="xxx"
FTPPassword="yyy"
array = []
zip_location="C:\\BIM\\delete"
xml_location="C:\\BIM\\xmls"
logfile="C:\\scripts"
passed_windows,failed_windows,passed_java,failed_java,control=[],[],[],[],[]
windows_list,java_list=[],[]
ACI_lenght=0

#Checks whether the xml file generated from a previous run
#Skips if the file present

def check_xmls(ACI):
    dir = os.listdir(xml_location)
    for file in dir:
        file=str(file)
        if(file.startswith(ACI)):
            print(xml_location+"\\"+file+"\\deployit-manifest.xml")
            if os.path.exists(xml_location+"\\"+file+"\\deployit-manifest.xml"):
                return(True)
            else:
                print("File exists but no deployit-manifest.xml")
                recursive_rm(xml_location+"\\"+file+"\\deployit-manifest.xml")
                return(False)
    return(False)

#Common Function to write the message to a logfile and print to the console

def writelog(message):
    print(message)
    f = open(logfile + "\log.txt", "a")
    f.write(message+"\n")
    f.close()

#Remove temporary files from a previous run
	
def removeFiles():
    print("Cleaning Environment")
    if os.path.exists("deployit-manifest.xml"):
        os.remove("deployit-manifest.xml")
        print("Previous deployit-manifest.xml Removed!")
        writelog("Previous deployit-manifest.xml Removed!")
    if os.path.exists(zip_location):
        #        shutil.rmtree(zip_location)
        recursive_rm(zip_location)
        print("Temp Folder Removed:" + zip_location)
        writelog("Temp Folder Removed:" + zip_location)

# Custom recursive remove directory function
		
def recursive_rm(dir):
    if dir[-1] == os.sep: dir = dir[:-1]
    files = os.listdir(dir)
    for file in files:
        if file == '.' or file == '..': continue
        path = dir + os.sep + file
        if os.path.isdir(path):
            recursive_rm(path)
        else:
            os.unlink(path)
    os.rmdir(dir)
	
# Get data related to deployment package from architecture model

def getData(ACI):
    url = "https://genom.isbank/eamintegration/api/package"
    username = 'xxx'
    password = 'yyy'
    payload = "{'code': '"+ACI+"'}"
    headers = {
        'Content-Type': "application/json",
        'Authorization': "Basic",
        'Cache-Control': "no-cache"
    }

    response = requests.request("POST", url, data=payload, headers=headers, verify=False, auth=(username, password))
    data = json.loads(response.text)
    return (data)
	
# Decide whether package is .NET or Java	

def checkTechnology(data):
    try:
        if (data['iisinfo']):
            Technology="Windows"
    except:
        try:
            if (data['wasinfo']):
                Technology = "Java"
        except:
            Technology = ""
    return Technology
	
# Parse the raw data coming from Architectural model
        
def checkGenomData(data,ACI):
    WebsitePath,WebsiteName,ApplicationName,Protocol,Port, sitePath,IIS_Services_Root,WebsiteNameFull,Url,WinServiceName,WinServicePath,developers = "","","","","","","","","","","",""

    foundprod = False
    founduat = False
    foundint = False
    for i in range(0, len(data['iisinfo'])):
        if (data['iisinfo'][i]['env'] == 'prod'):
            foundprod = True
            prodindex = i
        elif (data['iisinfo'][i]['env'] == 'uat'):
            founduat = True
            uatindex = i
        elif (data['iisinfo'][i]['env'] == 'int'):
            foundint = True
            intindex = i

    if (foundprod):
        index = prodindex
    elif (founduat):
        index = uatindex
    elif (foundint):
        index = intindex


    developers = data['iisinfo'][index]['detail']['developers']
    try:
        packagename = data['package']['name']
    except:
        writelog("PackageName is Empty in the Genome Model")
        failed_windows.append(ACI + " :PackageName is Empty in the Genome Model")
        return
#        exit()
    WindowsServiceFlag = False
    if(data['package']['componenttype'] == ".NET Windows Service"):
        WindowsServiceFlag = "WinService"
    elif(data['package']['componenttype'] == ".NET Batch" or data['package']['componenttype'] == "Batch"):
        WindowsServiceFlag = "Batch"

    if (WindowsServiceFlag == False):
        WebsiteName=data['iisinfo'][index]['webSiteInfo']['siteName']
        if (not WebsiteName):
            writelog("SiteName is Empty in the Genome Model")
            failed_windows.append(ACI + " :SiteName is Empty in the Genome Model")
            return
        #        exit()

    if (WindowsServiceFlag == False):
        Url = data['iisinfo'][index]['webSiteInfo']['url']
        ApplicationName = Url.split(WebsiteName)[1]
        ApplicationName = ApplicationName[1:]
        WebsiteName = data['iisinfo'][index]['webSiteInfo']['siteName'].split('.')[0]
        if ("eadesktop" in WebsiteName):
            WebsiteName = "eadesktop"

        if (not WebsiteName):
            writelog("WebsiteName is Empty in the Genome Model")
            failed_windows.append(ACI + " :WebsiteName is Empty in the Genome Model")
            return
        #        exit()

        try:
            data['iisinfo'][index]['webSiteInfo']['httpsBinding']
            Protocol="https"
        except:
            try:
                data['iisinfo'][index]['webSiteInfo']['httpBinding']
                Protocol = "http"
            except:
                writelog("Http/Https Binding Info is Empty in the Genome Model")
                failed_windows.append(ACI + "Http/Https Binding Info is Empty in the Genome Model")
                return
        #        exit()

        if (Protocol =='https'):
            Port = data['iisinfo'][index]['webSiteInfo']['httpsBinding'].split(',')[0].split(':')[1]
        else:
            Port = data['iisinfo'][index]['webSiteInfo']['httpBinding'].split(',')[0].split(':')[1]


        sitePath=data['iisinfo'][index]['webSiteInfo']['sitePath']
        if (not sitePath):
            writelog("SitePath is Empty in the Genome Model")
            failed_windows.append(ACI + "SitePath is Empty in the Genome Model")
            return
        #        exit()

        WebsitePath=data['iisinfo'][index]['detail']['paths']
        WebsitePath = WebsitePath[0].replace("$",":")
        if (not WebsitePath):
            writelog("Path Value is Empty in the Genome Model")
            failed_windows.append(ACI + "Path Value is Empty in the Genome Model")
            return
        #        exit(

        WebsitePath = WebsitePath[WebsitePath.find(":")-1:]
        IIS_Services_Root='C:\\Inetpub'
        WebsiteNameFull = data['iisinfo'][index]['webSiteInfo']['siteName']
    Path=data['iisinfo'][index]['detail']['paths'][0]
    split_index = Path.find('$')-1
    Path=Path[split_index:].replace('$',':')
    Developers = data['iisinfo'][0]['detail']['developers']
    if (WindowsServiceFlag == "WinService"):
        try:
            WinServiceName = data['iisinfo'][prodindex]['windowsServiceInfo']['serviceName']
            WinServicePath = data['iisinfo'][prodindex]['windowsServiceInfo']['servicePath']
        except:
            pass
        if (WinServiceName == "" or WinServicePath == ""):
            try:
                WinServiceName = data['iisinfo'][uatindex]['windowsServiceInfo']['serviceName']
                WinServicePath = data['iisinfo'][uatindex]['windowsServiceInfo']['servicePath']
            except:
                pass
            if (WinServiceName == "" or WinServicePath == ""):
                try:
                    WinServiceName = data['iisinfo'][intindex]['windowsServiceInfo']['serviceName']
                    WinServicePath = data['iisinfo'][intindex]['windowsServiceInfo']['servicePath']
                except:
                    writelog(ACI + " WindowsServiceName is Empty in the Genome Model")
                    failed_windows.append(ACI + " WindowsServiceName is Empty in the Genome Model")
                    return



    return WebsiteName, WebsitePath, ApplicationName, Protocol, Port, sitePath, packagename, IIS_Services_Root, WebsiteNameFull, Url, WindowsServiceFlag, Path,WinServiceName,WinServicePath, Developers

# Parse the raw data coming from Architectural model for Java
	
def checkWASGenomData(data,ACI):
    try:
        PackageName = data['package']['name']
    except:
        print("PackageName is Empty in the Genome Model")
        writelog("PackageName is Empty in the Genome Model")
        failed_java.append(ACI + " :PackageName is Empty in the Genome Model")
        return

    try:
        RepoName = data['package']['repo']
    except:
        writelog("PackageRepo is Empty in the Genome Model")
        failed_java.append(ACI + " :PackageRepo is Empty in the Genome Model")
        return

    ProjectName =  RepoName.split('/')[4]
    if (not PackageName):
        print("PackageName is Empty in the Genome Model")
        writelog("PackageName is Empty in the Genome Model")
        failed_java.append(ACI + " PackageName is Empty in the Genome Model")
        return

    return PackageName,ProjectName

#Cloning Project Package from TFS --Not in use 

def get_deployment_package_GIT(GITUserName,GITPassword,projectname,packagename):
    gitConnectionString="https://"+GITUserName+":"+GITPassword+"@scoretfs.isbank/ISBANK/"+projectname+"/_git/"+packagename
    print(gitConnectionString)
    call("git -c http.sslVerify=false clone --single -branch -b develop "+gitConnectionString)

#Cloning Project Package from a local FTP Repo 

def get_deployment_package(ip,port,username,password,projectname,packagename,zip_location):
    try:
        s=socket.socket()
        s.connect((ip,port))
#        print("port "+str(port)+" is open")
        ftp = ftplib.FTP(ip)
        print("Connecting to Yazilim Deposu FTP")
        ftp.login(FTPUserName,FTPPassword)
    except ftplib.error_perm:
        print("Cannot Connect To FTP")
        writelog("Cannot Connect To FTP")
        removeFiles()
        return
    #        exit()
    print("Connected to FTP")
    os.mkdir(zip_location)
    files = ftp.cwd(projectname)
    files = ftp.nlst()
    print(files)
    files.sort(reverse=True)
    found=False
    
    for file in files:
        if(found):
            return()
        if (file.startswith('P')):
            print(file)
            ftp.cwd(file)
            for filename in ftp.nlst():
                if (packagename in filename):
                    found=True
                    print("Copying The Package: "+filename)
                    writelog("Copying The Package: "+filename)
                    local_filename = os.path.join(zip_location, filename)
                    lf = open(local_filename, "wb")
                    ftp.retrbinary("RETR " + filename, lf.write)
                    print("File Copied To: "+zip_location)
                    writelog("File Copied To: "+zip_location)
                    lf.close()
            ftp.cwd('..')
    
    for file in files:
        if(found):
            return()
        if (file.startswith('U')):
            print(file)
            ftp.cwd(file)
            for filename in ftp.nlst():
                if (packagename in filename):
                    found=True
                    print("Copying The Package: "+filename)
                    writelog("Copying The Package: "+filename)
                    local_filename = os.path.join(zip_location, filename)
                    lf = open(local_filename, "wb")
                    ftp.retrbinary("RETR " + filename, lf.write)
                    print("File Copied To: "+zip_location)
                    writelog("File Copied To: "+zip_location)
                    lf.close()
            ftp.cwd('..')

    for file in files:
        if(found):
            return()
        if (file.startswith('I')):
            print(file)
            ftp.cwd(file)
            for filename in ftp.nlst():
                if (packagename in filename):
                    found=True
                    print("Copying The Package: "+filename)
                    writelog("Copying The Package: "+filename)
                    local_filename = os.path.join(zip_location, filename)
                    lf = open(local_filename, "wb")
                    ftp.retrbinary("RETR " + filename, lf.write)
                    print("File Copied To: "+zip_location)
                    writelog("File Copied To: "+zip_location)
                    lf.close()
            ftp.cwd('..')


#Convert listing output into an array
			
def listdir(d,array):

    if not os.path.isdir(d):
        array.append(d)
    else:
        for item in os.listdir(d):
            listdir((d + '\\' + item) if d != '\\' else '\\' + item,array)
    return array

#Finds .ear/war/zip file and extracts it

def extract_zip(zip_location):
    found='1'
    PackageType=""
    while True:
        if (found=='0'):
            break
        found='0'
        array=[]
        files=listdir(zip_location,array)
 #   print(files)
        for file in files:
 #       print(file)
            if (file.endswith('.ear') or file.endswith('.war') or file.endswith('.zip')):
                if ((file.endswith('.ear') or file.endswith('.war')) and PackageType == ""):
                    PackageType=file[-3:]
                found='1'
                zip_ref = zipfile.ZipFile(file, 'r')
                os.mkdir(file.replace(".","_"))
                zip_ref.extractall(file.replace(".","_"))
                zip_ref.close()
                os.remove(file)
                break

    return PackageType
	
#Finds the file in a directory and returns the name

def find_xml(zip_location,XmlName, array):
    array=[]
    xml_file=""
    files=listdir(zip_location,array)
    for file in files:
        if (file.endswith(XmlName)):
            xml_file=file
            return(xml_file)
    return (xml_file)

#Finds multiple files in a directory and returns the names

def find_xmls(zip_location,XmlName, array):
    arrays=[]
    files=listdir(zip_location,array)
    for file in files:
        if (file.endswith(XmlName)):
            arrays.append(file)
    return(arrays)

#Gets Java parameters from Architecture Model
	
def get_WASParams(PackageType,ProjectName,zip_location,ACI,control):
    if PackageType == "ear":
        contextroot = ""
    elif PackageType == "war" and ProjectName == "EWTATANE":
        contextroot = PackageName.split("-")[0]
    else:
        xml_paths = find_xmls(zip_location, ".xml", array)
        found = False
        for xml_path in xml_paths:
            with open(xml_path) as myfile:
                print("XMLs inside War File: " + xml_path)
                writelog("XMLs inside War File: " + xml_path)
                myfilecontent = myfile.read()
                if (re.search('Context-Root', myfilecontent, re.IGNORECASE) or re.search('ContextRoot', myfilecontent,
                                                                                         re.IGNORECASE)):
                    found = True
                    print(xml_path)
                    writelog(xml_path)
                    contextroot = PackageName.split("-")[0]
                    print("Context Root'u Test Edin!!")
                    writelog("Context Root'u Test Edin!!")
                    control.append(ACI)
            if (not found):
                contextroot = PackageName.split("-")[0]

    pom_properties = find_xml(zip_location, "pom.properties", array)
    if(pom_properties==""):
        print("Package doesn't Have a POM PROPERTIES!! Searching for POM.XML...")
        writelog("Package doesn't Have a POM PROPERTIES!! Searching for POM.XML...")
    else:
        groupid, artifactid, version = parse_pom(pom_properties,"properties")
        if (version !="" and groupid !="" and artifactid !=""):
            return contextroot,groupid,artifactid,version,control

    pom_xml = find_xml(zip_location, "pom.xml", array)
    if (pom_xml == ""):
        print("Package doesn't Have a POM FILE!! Exiting...")
        writelog("Package doesn't Have a POM FILE!! Exiting...")
        removeFiles()
        failed_java.append(ACI+" Package doesn't Have a POM FILE!!")
        return
    #        exit()
    else:
        groupid, artifactid, version = parse_pom(pom_xml,"xml")
        return contextroot,groupid,artifactid,version,control

#Parse POM.XML for version,groupId,artifactId
		
def parse_pom(pom_xml,pom_type):
    source = open(pom_xml)
    if (pom_type=="properties"):
        print("Pom Properties Found... ")
        writelog("Pom Properties Found... ")
        lines = source.readlines()
        for line in lines:
            if ("version" in line):
                version=line.split("=")[1].strip()
            elif("groupId" in line):
                groupid=line.split("=")[1].strip()
            elif("artifactId" in line):
                artifactid=line.split("=")[1].strip()
        if (version !="" and groupid !="" and artifactid !=""):
            source.close()
            return groupid,artifactid,version
    tree = ET.parse(source)
    root = tree.getroot()
    for elem in tree.iter():
        #        if (elem.tag.endswith('packaging')):
        #                print(elem.text)
        #                packagetype = elem.text
        if (elem.tag.endswith('parent')):
            for subelem in elem.iter():
                if (subelem.tag.endswith('groupId')):
                    groupid = subelem.text.strip()
#                    print("groupID:" + groupid)
                elif (subelem.tag.endswith('artifactId')):
                    artifactid = subelem.text
#                    print("artifactid:" + artifactid)
                elif (subelem.tag.endswith('version')):
                    version = subelem.text
#                    print("version:" + version)
        else:
            if (elem.tag.endswith('groupId')):
                groupid = elem.text.strip()
    #                    print("groupID:" + groupid)
            elif (elem.tag.endswith('artifactId')):
                artifactid = elem.text
    #                    print("artifactid:" + artifactid)
            elif (elem.tag.endswith('version')):
                version = elem.text

    source.close()
    return groupid,artifactid,version
	
#Parse WEB.XML for context-root

def parse_web(web_xml):
    source = open(web_xml)
    tree = ET.parse(source)
    root = tree.getroot()
    for elem in tree.iter():
        #        if (elem.tag.endswith('packaging')):
        #                print(elem.text)
        #                packagetype = elem.text
        if (elem.tag.endswith('context-param')):
            for subelem in elem.iter():
                if (subelem.tag('webAppRootKey')):
                    contextroot = subelem.text.strip()
                    print("contextroot:" + contextroot)
                    writelog("contextroot:" + contextroot)
    source.close()
    return contextroot

#Determine deployit-manifest type

def determine_xml_type(WebsiteName,Url, WindowsServiceFlag,PackageType,Technology, Protocol):
    if (Technology=='Windows'):
        if (WindowsServiceFlag == "WinService"):
            xml_type = 'windowsservice_deployit_manifest'
            return xml_type
        elif(WindowsServiceFlag == "Batch"):
            xml_type = 'windowsbatch_deployit_manifest'
            return xml_type
        else:
            if ((not "/" in Url) and Protocol=="http"):
                xml_type='website_deployit_manifest'
                return xml_type
            elif ((not "/" in Url) and Protocol == "https"):
                xml_type='website_deployit_ssl_manifest'
                return xml_type
            else:
                xml_type='webapplication_deployit_manifest'
                return xml_type
    else:
        if (PackageType == "ear"):
            xml_type='ear-deployit-manifest'
            return xml_type
        elif (PackageType == "war" and ProjectName=="EWTATANE"):
            xml_type='war-tane-deployit-manifest'
            return xml_type
        elif (PackageType == "war" and ProjectName!="EWTATANE"):
            xml_type='war-deployit-manifest'
            return xml_type

#Sends E-Mail

def sendemail(frommail, tomail, ccmail, ACI, projectname, packagename):
    subject = "Kýrmýzý Hat Geçiþi Deployit Manifest -" + projectname + " " + packagename

    COMMASPACE = ', '
    msg = MIMEMultipart()
    msg['From'] = frommail
    msg['To'] = COMMASPACE.join(tomail)
    msg['Cc'] = COMMASPACE.join(ccmail)
    msg['Subject'] = subject
    dirname, filename = os.path.split(os.path.abspath(sys.argv[0]))
    rbody = open(os.path.join(dirname, "textfile.txt"), 'r')
    body = MIMEText(
        rbody.read().replace("ProjectName", projectname).replace("PackageName", packagename).replace("ACIid", ACI),
        'html', 'latin5')
    msg.attach(body)
    rbody.close()
    file_location = os.path.join(dirname, "deployit-manifest.xml")
    filename = ntpath.basename(file_location)
    attachment = open(file_location, "rb")
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
    msg.attach(part)
    msg["Content-type"] = "text/html;charset=latin5"
    s = smtplib.SMTP('smtpgwuat.isbank', 25)
    text = msg.as_string().encode('latin5')
    s.sendmail(frommail, tomail, text)
    s.quit()

#Generate the deployit-manifest.xml File
	
def generate_xml(xml_type, WebsiteName, WebsitePath, ApplicationName, Protocol, Port, sitePath, packagename,
                 IIS_Services_Root, Path,groupid,artifactid,version,contextroot,xml_location,winServiceName,winServicePath):
    if (WebsiteName != "eadesktop"):
        WebsiteNameXml=WebsiteName+ """.{{DomainName}}"""
    else:
        WebsiteNameXml = WebsiteName + """{{DomainName}}"""
        WebsitePath=WebsitePath.replace("inetpub\\tanewebsube","inetpub\\eadesktop")
    xml_path = xml_location+"\\"+ACI+"_"+packagename
    if os.path.exists(xml_path):
        recursive_rm(xml_path)
        print("XML Folder Removed:" + xml_path)
        writelog("XML Folder Removed:" + xml_path)
    os.mkdir(xml_path)
    print("XML Folder Created:" + xml_path)
    writelog("XML Folder Created:" + xml_path)



    if (xml_type=='website_deployit_manifest'):
        website_deployit_manifest="""<?xml version="1.0" encoding="UTF-8"?>
<udm.DeploymentPackage version="%BuildNumber%" application=\""""+ACI+"""">
  <application />
    <orchestrator>
        <value>sequential-by-container</value>
    </orchestrator>
  <deployables>
  <iis.WebContent name="/"""+packagename+"""_WebContent" file="/_PublishedWebsites/"""+packagename+"""">
      <tags />
      <scanPlaceholders>true</scanPlaceholders>
      <excludeFileNamesRegex>.*EntityFramework.*</excludeFileNamesRegex>
	<targetPath>"""+sitePath+"""</targetPath>
    </iis.WebContent>
      <iis.WebsiteSpec name="/"""+packagename+"""_WebSite">
      <websiteName>"""+WebsiteNameXml+"""</websiteName>
      <physicalPath>"""+sitePath+"""</physicalPath>
      <applicationPoolName>"""+WebsiteName+""".{{DomainName}}</applicationPoolName>
      <bindings>
        <iis.WebsiteBindingSpec name=\""""+packagename+""".WebsiteBindingSpec">
          <protocol>""" + Protocol + """</protocol>
          <port>""" + Port + """</port>
          <hostHeader>"""+WebsiteName+""".{{DomainName}}</hostHeader>
        </iis.WebsiteBindingSpec>
      </bindings>
    </iis.WebsiteSpec>
    <iis.ApplicationPoolSpec name="/"""+packagename+"""ApplicationPoolSpec">
      <applicationPoolName>"""+WebsiteName+""".{{DomainName}}</applicationPoolName>
      <managedRuntimeVersion>v4.0</managedRuntimeVersion>
      <serviceAccount>NetworkService</serviceAccount>
      <enable32BitAppOnWin64>true</enable32BitAppOnWin64>
    </iis.ApplicationPoolSpec>	
  </deployables>
  <applicationDependencies />
  <dependencyResolution>LATEST</dependencyResolution>
  <undeployDependencies>false</undeployDependencies>
</udm.DeploymentPackage>"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(website_deployit_manifest)
        f.close()
        passed_windows.append(ACI)
    elif (xml_type == 'website_deployit_ssl_manifest'):
        website_deployit_ssl_manifest = """<?xml version="1.0" encoding="UTF-8"?>
    <udm.DeploymentPackage version="%BuildNumber%" application=\"""" + ACI + """">
      <application />
      <orchestrator>
        <value>sequential-by-container</value>
      </orchestrator>
      <deployables>
      <iis.WebContent name="/""" + packagename + """_WebContent" file="/_PublishedWebsites/""" + packagename + """">
          <tags />
          <scanPlaceholders>true</scanPlaceholders>
          <excludeFileNamesRegex>.*EntityFramework.*</excludeFileNamesRegex>
    	<targetPath>""" + sitePath + """</targetPath>
        </iis.WebContent>
          <iis.WebsiteSpec name="/""" + packagename + """_WebSite">
          <websiteName>""" + WebsiteNameXml + """</websiteName>
          <physicalPath>""" + sitePath + """</physicalPath>
          <applicationPoolName>""" + WebsiteName + """.{{DomainName}}</applicationPoolName>
          <bindings>
            <iis.WebsiteBindingSpec name=\"""" + packagename + """.WebsiteBindingSpec">
              <protocol>{{Protocol}}</protocol>
              <port>{{Port}}</port>
              <certificateName>{{CertificateName}}</certificateName>
              <hostHeader>""" + WebsiteName + """.{{DomainName}}</hostHeader>
            </iis.WebsiteBindingSpec>
          </bindings>
        </iis.WebsiteSpec>
        <iis.ApplicationPoolSpec name="/""" + packagename + """ApplicationPoolSpec">
          <applicationPoolName>""" + WebsiteName + """.{{DomainName}}</applicationPoolName>
          <managedRuntimeVersion>v4.0</managedRuntimeVersion>
          <serviceAccount>NetworkService</serviceAccount>
          <enable32BitAppOnWin64>true</enable32BitAppOnWin64>
        </iis.ApplicationPoolSpec>	
      </deployables>
      <applicationDependencies />
      <dependencyResolution>LATEST</dependencyResolution>
      <undeployDependencies>false</undeployDependencies>
    </udm.DeploymentPackage>"""

        f = open(xml_path + "\deployit-manifest.xml", "w")
        f.write(website_deployit_ssl_manifest)
        f.close()
        passed_windows.append(ACI)
    elif(xml_type == 'webapplication_deployit_manifest'):
        webapplication_deployit_manifest="""<?xml version="1.0" encoding="UTF-8"?>
<udm.DeploymentPackage version="%BuildNumber%" application=\""""+ACI+"""">
  <application />
  <orchestrator>
        <value>sequential-by-container</value>
  </orchestrator>
  <deployables>
  <iis.WebContent name="/"""+packagename+"""_WebContent" file="/_PublishedWebsites/"""+packagename+"""">
       <scanPlaceholders>true</scanPlaceholders>
      <excludeFileNamesRegex>.*EntityFramework.*</excludeFileNamesRegex>
      <targetPath>"""+WebsitePath+"""</targetPath>
    </iis.WebContent>
  <iis.ApplicationSpec name="/"""+packagename+""".ApplicationSpec">
      <applicationPath>"""+ApplicationName+"""</applicationPath>
      <websiteName>"""+WebsiteNameXml+"""</websiteName>
      <physicalPath>"""+WebsitePath+"""</physicalPath>
      <applicationPoolName>"""+WebsiteName+"""_"""+ApplicationName.replace("/","_")+"""</applicationPoolName>
      <authentication></authentication>
    </iis.ApplicationSpec>
    <iis.ApplicationPoolSpec name="/"""+packagename+""".ApplicationPoolSpec">
      <applicationPoolName>"""+WebsiteName+"""_"""+ApplicationName.replace("/","_")+"""</applicationPoolName>
      <managedRuntimeVersion>v4.0</managedRuntimeVersion>
      <enable32BitAppOnWin64>true</enable32BitAppOnWin64>
      <serviceAccount>NetworkService</serviceAccount>
    </iis.ApplicationPoolSpec>
  </deployables>
  <applicationDependencies />
  <dependencyResolution>LATEST</dependencyResolution>
  <undeployDependencies>false</undeployDependencies>
</udm.DeploymentPackage>"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(webapplication_deployit_manifest)
        f.close()
        passed_windows.append(ACI)
    elif (xml_type == 'website_webapplication_deployit_manifest'):
        website_webapplication_deployit_manifest="""<?xml version="1.0" encoding="UTF-8"?>
<udm.DeploymentPackage version="%BuildNumber%" application=\""""+ACI+"""">
  <application />
  <orchestrator>
        <value>sequential-by-container</value>
  </orchestrator>
  <deployables>
  <iis.WebContent name="/"""+packagename+"""_WebContent" file="/_PublishedWebsites/"""+packagename+"""">
      <tags />
      <scanPlaceholders>true</scanPlaceholders>
      <excludeFileNamesRegex>.*EntityFramework.*</excludeFileNamesRegex>
	<targetPath>"""+WebsitePath+"""</targetPath>
    </iis.WebContent>
      <iis.WebsiteSpec name="/"""+packagename+"""_WebSite">
      <websiteName>"""+WebsiteNameXml+"""</websiteName>
      <physicalPath>"""+sitePath+"""</physicalPath>
      <applicationPoolName>"""+WebsiteName+""".{{DomainName}}</applicationPoolName>
      <bindings>
        <iis.WebsiteBindingSpec name=\""""+packagename+""".WebsiteBindingSpec">
          <protocol>"""+Protocol+"""</protocol>
          <port>"""+Port+"""</port>
          <hostHeader>"""+WebsiteName+""".{{DomainName}}</hostHeader>
        </iis.WebsiteBindingSpec>
      </bindings>
    </iis.WebsiteSpec>
    <iis.ApplicationPoolSpec name="/"""+packagename+"""W_ApplicationPoolSpec">
      <applicationPoolName>"""+WebsiteName+""".{{DomainName}}</applicationPoolName>
      <managedRuntimeVersion>v4.0</managedRuntimeVersion>
      <serviceAccount>NetworkService</serviceAccount>
    </iis.ApplicationPoolSpec>
	 <iis.ApplicationSpec name="/"""+packagename+"""_ApplicationSpec">
      <tags />
      <applicationPath>"""+ApplicationName+"""</applicationPath>
       <websiteName>"""+WebsiteName+""".{{DomainName}}</websiteName>
      <physicalPath>"""+WebsitePath+"""\\</physicalPath>
      <applicationPoolName>"""+WebsiteName+"""_"""+ApplicationName.replace("/","_")+"""</applicationPoolName>
      <authentication />
    </iis.ApplicationSpec>
	 <iis.ApplicationPoolSpec name="/"""+packagename+"""_ApplicationPoolSpec">
      <tags />
      <applicationPoolName>"""+WebsiteName+"""_"""+ApplicationName.replace("/","_")+"""</applicationPoolName>
      <managedRuntimeVersion>v4.0</managedRuntimeVersion>
      <serviceAccount>NetworkService</serviceAccount>
      <enable32BitAppOnWin64>true</enable32BitAppOnWin64>
    </iis.ApplicationPoolSpec>
  </deployables>
  <applicationDependencies />
  <dependencyResolution>LATEST</dependencyResolution>
  <undeployDependencies>false</undeployDependencies>
</udm.DeploymentPackage>
"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(website_webapplication_deployit_manifest)
        f.close()
        passed_windows.append(ACI)
    elif (xml_type == 'windowsservice_deployit_manifest'):
        windowsservice_deployit_manifest="""<?xml version="1.0" encoding="utf-8"?>
<udm.DeploymentPackage application=\""""+ACI+"""" version="1.0">
	<deployables>
    <file.Folder name=\""""+packagename+""".Content" file=\""""+packagename+"""">
   <scanPlaceholders>true</scanPlaceholders>
<targetPath>"""+Path+"""</targetPath>
      <createTargetPath>true</createTargetPath>
    </file.Folder>
    <windows.ServiceSpec name="/****.ServiceSpec">
   <serviceName>"""+packagename+"""</serviceName>
      <serviceDisplayName>"""+packagename+""""</serviceDisplayName>
      <binaryPathName>"""+winServicePath+""""</binaryPathName>
      <dependsOn />
      <startupType>Automatic</startupType>
    </windows.ServiceSpec>
  </deployables>
</udm.DeploymentPackage>

"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(windowsservice_deployit_manifest)
        f.close()
        passed_windows.append(ACI)
        
    elif(xml_type=='windowsbatch_deployit_manifest'):
        windowsbatch_deployit_manifest="""<?xml version="1.0" encoding="utf-8"?>
<udm.DeploymentPackage application=\""""+ACI+"""" version="%BuildNumber%">
  <orchestrator>
        <value>sequential-by-container</value>
  </orchestrator>
  <deployables>
    <file.Folder name=\""""+packagename+""".Folder" file=\""""+packagename+"""">
      <targetPath>"""+Path+"""</targetPath>
      <scanPlaceholders>true</scanPlaceholders>
      <excludeFileNamesRegex>.*EntityFramework.*</excludeFileNamesRegex>
      <createTargetPath>true</createTargetPath>
    </file.Folder>
  </deployables>
</udm.DeploymentPackage>
"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(windowsbatch_deployit_manifest)
        f.close()
        passed_windows.append(ACI)
        
    elif (xml_type=='ear-deployit-manifest'):
        ear_deployit_manifest="""<?xml version="1.0" encoding="UTF-8"?>
<udm.DeploymentPackage version="%BuildNumber%" application=\""""+ACI+"""">
  <application />
  <orchestrator />
  <deployables>
    <was.Ear name=\""""+packagename+"""">
      <fileUri>maven:"""+groupid+""":"""+artifactid+""":ear:"""+version+"""</fileUri>
      <sharedLibraryNames />
      <additionalInstallFlags />
      <roleMappings />
      <roleUserMappings />
      <webServerNames />
      <runAsRoleMappings />
      <sessionManagers />
      <webModules />
      <ejbModules />
    </was.Ear>
  </deployables>
  <applicationDependencies />
  <dependencyResolution>LATEST</dependencyResolution>
  <undeployDependencies>false</undeployDependencies>
</udm.DeploymentPackage>"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(ear_deployit_manifest)
        f.close()
        passed_java.append(ACI)

    elif(xml_type == 'war-deployit-manifest'):
        war_deployit_manifest="""<?xml version="1.0" encoding="UTF-8"?>
<udm.DeploymentPackage version="%BuildNumber%" application=\""""+ACI+"""">
  <application />
  <orchestrator />
  <deployables>
    <was.War name=\""""+packagename+"""">
	  <fileUri>maven:"""+groupid+""":"""+artifactid+""":war:"""+version+"""</fileUri>
	  <sharedLibraryNames />
      <additionalInstallFlags />
      <roleMappings />
      <roleUserMappings />
	  <virtualHostName>default_host</virtualHostName>
      <contextRoot>"""+contextroot+"""</contextRoot>
      <webServerNames />
      <webModules />
      <sessionManagers />
    </was.War>
  </deployables>
  <applicationDependencies />
  <dependencyResolution>LATEST</dependencyResolution>
  <undeployDependencies>false</undeployDependencies>
</udm.DeploymentPackage>"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(war_deployit_manifest)
        f.close()
        passed_java.append(ACI)
    else:
        war_tane_deployit_manifest="""<?xml version="1.0" encoding="UTF-8"?>
<udm.DeploymentPackage version="%BuildNumber%" application=\""""+ACI+"""">
  <application />
  <orchestrator />
  <deployables>
    <was.War name=\""""+packagename.replace(".","_")+""""> 
      <fileUri>maven:"""+groupid+""":"""+artifactid+""":war:"""+version+"""</fileUri>
      <virtualHostName>default_host</virtualHostName> 
      <contextRoot>"""+contextroot+"""</contextRoot>
      <tags />
      <scanPlaceholders>false</scanPlaceholders>
      <sharedLibraryNames>
        <value>tane_shared_lib</value>
      </sharedLibraryNames>
      <additionalInstallFlags />
      <roleMappings>
        <entry key="ChrRole">AllAuthenticatedInTrustedRealms</entry>
      </roleMappings>
    </was.War>
  </deployables>
  <applicationDependencies />
  <dependencyResolution>LATEST</dependencyResolution>
  <undeployDependencies>false</undeployDependencies>
</udm.DeploymentPackage>
"""

        f = open(xml_path+"\deployit-manifest.xml", "w")
        f.write(war_tane_deployit_manifest)
        f.close()
        passed_java.append(ACI)


if __name__ == "__main__":
    writelog("-------------------------------------------------------")
    writelog("--------------------Starting---------------------------")
    writelog("-------------------------------------------------------")
    with open("ACIs.txt", "r") as ACIs:
        for ACI in ACIs:
            ACI_lenght=ACI_lenght+1
            ACI=ACI.strip()
            writelog("Running For ACI:" + ACI)
            xml_path = check_xmls(ACI)
            if (xml_path):
                writelog("XML Exists From Previous Run Exiting")
                passed_windows.append(ACI + " XML Exists From Previous Run Exiting")
                continue
            else:
                removeFiles()
                data = getData(ACI)
                writelog("Checking Technology in Genom")
                Technology = checkTechnology(data)
                writelog("Technology is: "+Technology)
                if (Technology==""):
                    writelog("IISInfo or WASInfo Field Doesnt Exist in Genom Model, Exiting!")
                    failed_java.append(ACI + " IISInfo or WASInfo Field Doesnt Exist in Genom Model, Exiting!")
                    continue
                writelog("This is a "+Technology+" Package")
                if(Technology == "Windows"):
                    windows_list.append(ACI)
                    GroupId, ArtifactId, Version, contextroot,PackageType="","","","",""
                    if(checkGenomData(data,ACI)is None):
                        failed_windows.append(ACI + " IISInfo Field Doesnt Exist in Genom Model, Exiting!")
                        continue
                    WebsiteName, WebsitePath, ApplicationName, Protocol, Port, sitePath, PackageName, IIS_Services_Root,WebsiteNameFull ,Url, WindowsServiceFlag, Path,WindowsServiceName,WindowsServicePath,Developer = checkGenomData(data,ACI)
                    if (not WindowsServiceFlag):
                        writelog("WebsiteName: "+WebsiteName)
                        writelog("WebsitePath: " + WebsitePath)
                        writelog("ApplicationName: " + ApplicationName)
                        writelog("Protocol: " + Protocol)
                        writelog("Port: " + Port)
                        writelog("sitePath: " + sitePath)
                        writelog("PackageName: " + PackageName)
                        writelog("IIS_Services_Root: " + IIS_Services_Root)
                    else:
                        writelog("Windows Servis Paketi: ")
                        writelog("Path: " + Path)
                    if (WindowsServiceFlag=="WinService"):
                        writelog("WinServiceName: " + WindowsServiceName)
                        writelog("WinServicePath: " + WindowsServicePath)



                    print("Developers: ")
                    print(Developer)
                else:
                    java_list.append(ACI)
                    if(checkWASGenomData(data,ACI)is None):
                        failed_java.append(ACI + " WASInfo Field Doesnt Exist in Genom Model, Exiting!")
                        continue
                    PackageName,ProjectName = checkWASGenomData(data,ACI)
 #                   get_deployment_package(ip, port, FTPUserName, FTPPassword, ProjectName, PackageName, zip_location)
                    get_deployment_package_GIT(GITUserName, GITPassword, ProjectName, PackageName)
                    PackageType = extract_zip(zip_location)
                    if (PackageType==""):
                        writelog("Cannot Find Package in Yazilimdeposu: "+PackageName+"_"+ProjectName)
                        failed_java.append(ACI + "Cannot Find Package in Yazilimdeposu: "+PackageName+"_"+ProjectName)
                        continue
                    writelog("Package Type is "+PackageType)
                    if(get_WASParams(PackageType,ProjectName,zip_location,ACI,control)is None):
                        failed_java.append(ACI + " get_WASParams failed")
                        continue
                    contextroot,GroupId,ArtifactId,Version,control = get_WASParams(PackageType,ProjectName,zip_location,ACI,control)
                    writelog("Project Name: " + ProjectName)
                    writelog("Package Name: " + PackageName)
                    writelog("Context-Root: " + contextroot)
                    writelog("GroupID: "+GroupId)
                    writelog("ArtifactID: " + ArtifactId)
                    writelog("Version: " + Version)
                    WebsiteNameFull, Url, WindowsServiceFlag ="","",""
                    WebsiteName, WebsitePath, ApplicationName, Protocol, Port, sitePath, IIS_Services_Root, Path="","","","","","","",""

                xml_type = determine_xml_type(WebsiteNameFull, Url, WindowsServiceFlag,PackageType,Technology,Protocol)
                writelog("XML Type: "+xml_type)
                generate_xml(xml_type, WebsiteName, WebsitePath, ApplicationName, Protocol, Port, sitePath, PackageName,
                         IIS_Services_Root, Path,GroupId,ArtifactId,Version,contextroot,xml_location,WindowsServiceName,WindowsServicePath)
        writelog("---------------SUMMARY--------------------")
        writelog("Number of ACIs in the List: "+str(ACI_lenght))
        writelog("Number of ACIs Windows: "+str(len(windows_list)))
        writelog("Number of ACIs Java: "+str(len(java_list)))
        writelog("--------------SUCCESSES-------------------")
        writelog("Number of Files Created Windows: " + str(len(passed_windows)))
        for passed in passed_windows:
            writelog(passed)
        writelog("Number of Files Created Java: " + str(len(passed_java)))
        for passed in passed_java:
            writelog(passed)
        writelog("-------------FAILED ACIs------------------")
        writelog("Number of Files Failed Windows: " + str(len(failed_windows)))
        for fail in failed_windows:
            writelog(fail)
        writelog("Number of Files Created Java: " + str(len(failed_java)))
        for fail in failed_java:
            writelog(fail)
        writelog("--------ACIs TO CHECK CONTEXT ROOT--------")
        writelog("Number of Files To Be Checked: "+str(len(control)))
        for fail in control:
            writelog(fail)
#    toMail = ["bengi.icli@isbank.com.tr", "ugur.ustaoglu@isbank.com.tr"]

#    sendemail("ugur.ustaoglu@isbank.com.tr", toMail, "ugur.ustaoglu@isbank.com.tr", ACI, ProjectName,PackageName)



from suds.client import Client
from suds.xsd.doctor import Import
from suds.xsd.doctor import ImportDoctor
from suds.plugin import MessagePlugin
import base64
import argparse
from getpass import getpass
import os
import sys
import platform
from datetime import datetime

# This is monkey patching SSL to not validate the certificate
import ssl
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context
# End of SSL monkey patch

# Variable assignments
ip, user, pwd = '', '', ''
exitcode = 0
loginfo = ''


def axltoolkit(axlver):
    # This block checks the path you are in and uses the axlsqltoolkit
    # under the path of the script location.
    fileDir = os.path.dirname(os.path.realpath('__file__'))
    rel_path = 'axlsqltoolkit/schema/' + str(axlver) + '/AXLAPI.wsdl'
    fullfilepath = os.path.join(fileDir, rel_path)
    # If it's Windows we need to fix the backslashes to forward slashes.
    normalizedfilepath = fullfilepath.replace('\\', '/')
    # Join the file path depending on the system
    if platform.system() == 'Windows':
        wsdl = 'file:///' + normalizedfilepath
    else:
        wsdl = 'file://' + normalizedfilepath
    return wsdl


def main():
    parser = argparse.ArgumentParser(description='UCM Script Options')
    parser.add_argument('-i', dest='host', help='Please specify UCM address.')
    parser.add_argument('-u', dest='user', help='Enter Username.')
    parser.add_argument('-p', dest='pwd', help='Enter Password.')
    parser.add_argument('-v', dest='ver', help='Enter Version. (10.0, 10.5, 11.0, 11.5)')
    parser.add_argument('-c', dest='currentpartition', help='Enter current partition')
    parser.add_argument('-n', dest='newpartition', help='Enter new partition')
    parser.add_argument('-a', dest='sso', help='SSO enabled "true" or "false" - "false is assumed"')
    parser.add_argument('-l', dest='log', help='Log file name.')
    options = parser.parse_args()
    global ip, user, pwd, client, axlver, wsdl, loginfo
    if options.ver:
        axlver = options.ver
    else:
        axlver = raw_input("Please Enter the version of the CUCM cluster (10.0, 10.5, 11.0, 11.5) > ")
    if options.host:
        ip = options.host
    else:
        ip = raw_input("Please Enter the IP Address or Hostname of your CUCM > ")
    if options.user:
        user = options.user
    else:
        user = raw_input("Please Enter Your CUCM User ID > ")
    if options.pwd:
        pwd = options.pwd
    else:
        pwd = getpass("Please Enter Your Password > ")
    if options.sso:
        ssocheck = options.sso
    else:
        ssocheck = "false"
    if options.log:
        logfile = options.log + datetime.now().strftime('%Y-%m-%d-%H%M%S') + '.log'
    else:
        logfile = 'lastlog' + datetime.now().strftime('%Y-%m-%d-%H%M%S') + '.log'
    tns = 'http://schemas.cisco.com/ast/soap/'
    imp = Import('http://schemas.xmlsoap.org/soap/encoding/',
                 'http://schemas.xmlsoap.org/soap/encoding/')
    imp.filter.add(tns) 
    location = 'https://' + ip + ':8443/axl/'
    wsdl = axltoolkit(axlver)
    if ssocheck == "true":
        base64string = base64.encodestring('%s:%s' % (user, pwd)).replace('\n', '')
        authenticationHeader = {
            "SOAPAction" : "ActionName",
            "Authorization" : "Basic %s" % base64string
        }
        try:
            client = Client(wsdl,location=location,faults=False,plugins=[ImportDoctor(imp)],
                    headers=authenticationHeader)
        except:
            print "Error with version or IP address of server. Please try again."
            sys.exit()

    else:
        try:
            client = Client(wsdl, location=location, faults=False,
                        plugins=[ImportDoctor(imp)], username=user, password=pwd)
        except:
            print "Error with version or IP address of server. Please try again."
            sys.exit()
    try:
        verresp = client.service.getCCMVersion()
    except:
        print('Unknown Error. Please try again.')
        sys.exit()
    if verresp[0] == 401:
        print('Authentication failure. Wrong username or password.')
        sys.exit()
    cucmver = verresp[1]['return'].componentVersion.version
    cucmsplitver = cucmver.split('.')
    cucmactualver = cucmsplitver[0] + '.' + cucmsplitver[1]
    print('This cluster is version ' + cucmver)
    if axlver != cucmactualver:
        print('You chose the wrong version. The correct version is ') + cucmactualver
        print('Please choose the correct version next time.')
        sys.exit()
    if options.currentpartition:
        partold = options.currentpartition
    else:
        partold = raw_input('Current Partition > ')
    if options.newpartition:
        partnew = options.newpartition
    else:
        partnew = raw_input('New Partition > ')
    while exitcode != 1:
        dntochange = raw_input('Number to be modified? Hit <CR> to exit. > ')
        if dntochange == '':
            with open(logfile, 'w') as f:
                f.write(loginfo)
            break
        current_line = client.service.getLine(pattern=dntochange, routePartitionName = partold)
        resp = client.service.updateLine(pattern=dntochange, routePartitionName = partold, newRoutePartitionName=partnew)
        if resp[0] == 200:
            print ("Success - Changed DN %s to Partition %s." % (dntochange,partnew))
            loginfo = loginfo + "\nSuccess - Changed DN %s to Partition %s." % (dntochange,partnew)
        else:
            print ("Problem finding DN %s in Partition %s" % (dntochange,partold))
            loginfo = loginfo + "\nProblem finding DN %s in Partition %s" % (dntochange,partold)
            print resp



if __name__ == '__main__':
    main()


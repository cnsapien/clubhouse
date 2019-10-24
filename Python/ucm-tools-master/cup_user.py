# szelenka 2011-06-30
# script file to automate the user provisioning in CUP/CUCM
# takes output from CUCM, then manipulates it into new CSV files
# which can them be uploaded into CUP and CUCM to automate the 
# creation of features for the users defined in the userFile

import sys
import os.path
import getopt
import csv
import re
import datetime
from time import time

file_uid = ''
app_dial_rule = []
softphone_ids = []
csv_files = []

def usage():
  print 'Bulk device/user CSV generator for CUCM/CUP configuration'
  print 'USAGE:'
  print ' python '+sys.argv[0]+' --userFile="" --phoneFile="" [OPTIONAL: --presenceGroupFile="" --groupFile="" --roleFile=""]'
  print '\n'
  print 'All files must be obtained from the Cisco Unified Communications Manager, Bulk Administration tool.'
  print '\n'
  print '--userFile:'
  print '  "Users > Export Users" with "All User Format" selected'
  print '  this is the list of users you wish to configure for CUP and CUPC'
  print '  the script will create a softphone for each user and defaults the SUBSCRIBE CSS to the associated line CSS'
  print '  as well as the various other configuration to the device the line is associated with and use Adjunct Licensing when available'
  print '  also defines the user PIN to "12345" if the PIN is not already set'
  print '\n'
  print '--phoneFile:'
  print '  "Phones > Export Phones > All Details"'
  print '  this is the list of phones you wish to associate users with to use CUP and CUPC'
  print '  the script will find and associate users in "userFile" with the Directory Number Line Appearance in "phoneFile"'
  print '  match is determined by the users right-most "Telephone Number" attribute which matches a Directory Number'
  print '  the script can also update the Directory Number CID with the newly associated user display name'
  print '\n'
  print '--presenceGroupFile:'
  print '  "Import/Export > Export" with "System Data > Presence Group" selected'
  print '  this is the list of all Presence Groups defined on the system'
  print '  the script will find and associate users in "userFile" with the Standard group'
  print '\n'
  print '--groupFile:'
  print '  "Import/Export > Export" with "User Data > User Group" selected'
  print '  this is the list of all User Groups defined on the system'
  print '  the script will find and associate users in "userFile" with the necessary group(s) to use CUP and CUPC'
  print '\n'
  print '--roleFile:'
  print '  "Import/Export > Export" with "User Data > Role" selected'
  print '  this is the list of all Roles defined on the system'
  print '  the script will find and associate users in "userFile" with the necessary role(s) to use CUP and CUPC'
  

def main(argv):
  global csv_files, softphone_ids
  badfiles = []
  userFile = ''
  phoneFile = ''
  presenceGroupFile = ''
  groupFile = ''
  roleFile = ''
  ldapFile = ''
  try:
    opts, args = getopt.getopt(argv, "h:", ["help", "userFile=", "phoneFile=", "presenceGroupFile=", "groupFile=", "roleFile=", "ldapFile="])
  except getopt.GetoptError:
    usage()
    sys.exit(2)
  for opt, arg in opts:
    if opt in ('-h', '--help'):
      usage()
      sys.exit()
    if opt in ('--userFile'):
      userFile = arg
    if opt in ('--phoneFile'):
      phoneFile = arg
    if opt in ('--presenceGroupFile'):
      presenceGroupFile = arg
    if opt in ('--groupFile'):
      groupFile = arg
    if opt in ('--roleFile'):
      roleFile = arg
    if opt in ('--ldapFile'):
      ldapFile = arg
  
  if not os.path.isfile(userFile):
    badfiles.append({'name':'userFile','text':userFile})
  if not os.path.isfile(phoneFile):
    badfiles.append({'name':'phoneFile','text':phoneFile})
    
  if os.path.isfile(presenceGroupFile):
    csv_files.append({'type':'presence_group','file':presenceGroupFile,'obj':{}})
  if os.path.isfile(groupFile):
    csv_files.append({'type':'group','file':groupFile,'obj':{}})
  if os.path.isfile(roleFile):
    csv_files.append({'type':'role','file':roleFile,'obj':{}})
  if os.path.isfile(ldapFile):
    csv_files.append({'type':'ldap','file':ldapFile,'obj':{}})

  if len(badfiles) != 0:
    print ''
    for f in badfiles:
      print f['name']+': "'+f['text']+'" does not exist'
    print '\nexecute: python '+sys.argv[0]+' --help for more information\n'
    sys.exit()
  
  csv_files = []
  csv_files.append({'type':'user','file':userFile,'obj':{}})
  csv_files.append({'type':'phone','file':phoneFile,'obj':{}})
  
  for c in csv_files:
    open_file(c)
  
  new_files = []
  # this file will associate the user with a line appearance to use CUP/CUPC
  new_files.append({
    'created':False,
    'type':'Line Appearance',
    'target':'User Line Appearance',
    'transaction_type':'Update Line Appearance - Custom File',
    'destination':'Users > Line Appearance > Update Line Appearance',
    'fields': ['User ID','Device','Directory Number','Partition'], 
    'file':''
  })
  # this file will allow the admin to update all users information to use CUP/CUPC
  #TODO: assign Controlled Devices and Primary Extension?
  new_files.append({
    'created':False,
    'type':'Users',
    'target':'Users',
    'transaction_type':'Update Users - Custom File',
    'destination':'Users > Update Users',
    'fields': ['USER ID','PRESENCE GROUP','SUBSCRIBE CALLING SEARCH SPACE','ALLOW CONTROL OF DEVICE FROM CTI','USER GROUP 1','USER GROUP 2','USER GROUP 3','USER GROUP 4','PIN'], 
    'file':''
  })
  # this file will allow the admin to enable all CUP/CUPC users to use CUP/CUPC
  new_files.append({
    'created':False,
    'type':'CUP/CUPC',
    'target':'CUP Users',
    'transaction_type':'Update CUP Users - Custom File',
    'destination':'CUPS > Update CUPS/CUPC Users',
    'fields': ['User ID','Enable CUP','Enable CUPC'], 
    'file':''
  })
  # this file will allow the admin to update all CUP related users to ensure their deskphone is setup properly
  new_files.append({
    'created':False,
    'type':'Desk Phone',
    'target':'Phones',
    'transaction_type':'Update Phones - Custom File',
    'destination':'Phones > Update Phones > Custom File > (set "Allow Control of Device from CTI=checked", "PC Port=Enabled", "Video Capabilities=Enabled")',
    'fields': ['Device Name'],
    'file':''
  })
  # this file will create a CUPC softphone device in CUCM and associate it to the user and primary deskphone 
  new_files.append({
    'created':False,
    'type':'CUPC Softphone Adjunct',
    'target':'Phones',
    'transaction_type':'Insert Phones - Specific Details',
    'destination':'Phones > Insert Phones (using the CSF/CUPC Phone Template)',
    'fields': ['MAC ADDRESS','DESCRIPTION','PRIMARY PHONE','OWNER USER ID','DIGEST USER','Directory Number 1','Route Partition 1','Line CSS 1','Alerting Name 1','ASCII Alerting Name 1','Display 1','ASCII Display 1'],
    'file':''
  })
  new_files.append({
    'created':False,
    'type':'CUPC Softphone Standalone',
    'target':'Phones',
    'transaction_type':'Insert Phones - Specific Details',
    'destination':'Phones > Insert Phones (using the CSF/CUPC Phone Template)',
    'fields': ['MAC ADDRESS','DESCRIPTION','OWNER USER ID','DIGEST USER','Directory Number 1','Route Partition 1','Line CSS 1','Alerting Name 1','ASCII Alerting Name 1','Display 1','ASCII Display 1'],
    'file':''
  })
  # this file will create an Android dualphoen device in CUCM and associate it with the user and primary deskphone 
  new_files.append({
    'created':False,
    'type':'Android Softphone Adjunct',
    'target':'Phones',
    'transaction_type':'Insert Phones - Specific Details',
    'destination':'Phones > Insert Phones (using the Cisco Dual Mode for Android Phone Template that defines the "Product Specific Configuration Layout")',
    'fields':['MAC ADDRESS','DESCRIPTION','PRIMARY PHONE','OWNER USER ID','DIGEST USER','Directory Number 1','Route Partition 1'],
    'file':''
  })
  new_files.append({
    'created':False,
    'type':'Android Softphone Standalone',
    'target':'Phones',
    'transaction_type':'Insert Phones - Specific Details',
    'destination':'Phones > Insert Phones (using the Cisco Dual Mode for Android Phone Template that defines the "Product Specific Configuration Layout")',
    'fields':['MAC ADDRESS','DESCRIPTION','OWNER USER ID','DIGEST USER','Directory Number 1','Route Partition 1'],
    'file':''
  })
  # this file will create an iPhone dualphone device in CUCM and associate it with the user and primary deskphone
  new_files.append({
    'created':False,
    'type':'iPhone Softphone Adjunct',
    'target':'Phones',
    'transaction_type':'Insert Phones - Specific Details',
    'destination':'Phones > Insert Phones (using the Cisco Dual Mode for iPhone Phone Template that defines the "Product Specific Configuration Layout")',
    'fields':['MAC ADDRESS','DESCRIPTION','PRIMARY PHONE','OWNER USER ID','DIGEST USER','Directory Number 1','Route Partition 1'],
    'file':''
  })
  new_files.append({
    'created':False,
    'type':'iPhone Softphone Standalone',
    'target':'Phones',
    'transaction_type':'Insert Phones - Specific Details',
    'destination':'Phones > Insert Phones (using the Cisco Dual Mode for iPhone Phone Template that defines the "Product Specific Configuration Layout")',
    'fields':['MAC ADDRESS','DESCRIPTION','OWNER USER ID','DIGEST USER','Directory Number 1','Route Partition 1'],
    'file':''
  })
  # this file will update all the CUP users in CUP Administration to define all their vairous Profiles
  new_files.append({
    'created':False,
    'type':'CUP User Profile',
    'target':'CUP Users',
    'transaction_type':'Update CUP Users - Custom File',
    'destination':'CUPC/Deskphone > Update (You must have already configured the "Default Profile" for each CUPC setting)',
    'fields': ['User ID','Unity Profile','Meeting Place Profile','LDAP Profile','CTI Gateway Profile','Audio Profile','CCMCIP Profile','Enable MOC'],
    'file':''
  })
  
  dn_cnt = get_cnt(get_file('phone'),'Directory Number ')
  mapped_obj = {}
  mapped_obj['dn_list'] = get_dn_list(get_file('phone'),dn_cnt)
  mapped_obj['presence_group'] = get_presence_match(get_file('presence_group'))
  mapped_obj['user_group'] = get_group_match(get_file('group'),get_file('role'))
  for f in new_files:
    log(0, '---------- Generating '+f['type']+' file ...')
    reset_all_files()
    softphone_ids = []
    create_new_file(f,get_file('user'),mapped_obj)
    log_str = '---------- Successfully created '+f['type']+' file\n  Filename: '+os.getcwd()+'/'+f['file']+'\n  Upload this file to your Cisco Unified Communications Manager using the Bulk Administration tool as:'+'\n    Target: "'+f['target']+'"'+'\n    Transaction Type: "'+f['transaction_type']+'"'+'\n  Then once it is uploaded to CUCM, navigate to:'+'\n    Bulk Administration > '+f['destination']+'\n  Select "Run Immediately" and "Submit"'
    log(0,log_str)
  log(0, 'You can navigate to "Bulk Administration > Job Scheduler" to view the status of each job')
  log(0, 'Once all of the jobs have completed succesfully, your users should be CUP enabled!')
  print_app_dial_rule()
  
  for c in csv_files:
    c['obj'].close()
    
  return

def log(msg_type,print_str):
  err_file = sys.argv[0].split('.')[0]+'_LOGFILE_'+uid()+'.txt'
  o = open(err_file,'a')
  if msg_type == 1:
    msg = 'ERROR'
  elif msg_type == 2:
    msg = 'WARN '
  else:
    msg = 'INFO '
  ts = datetime.datetime.now()
  o.writelines(str(ts)+' ['+msg+'] '+print_str+'\n')
  o.close()
  
def uid():
  global file_uid
  if file_uid == '':
    file_uid = str(time()).split('.')[0]
  return file_uid
  
def open_file(csv_obj):
  csv_obj['obj'] = open(csv_obj['file'], 'rU')
  f = csv.reader(csv_obj['obj'], delimiter=',')
  csv_obj['csv'] = csv.DictReader(csv_obj['obj'],f.next(),delimiter=',')

def get_file(file_name,key=''):
  global csv_files
  for f in csv_files:
    if f['type'] == file_name:
      if key == '':
        return f['csv']
      else:
        return f[key]
  return ''
  
def reset_file(csv_obj):
  csv_obj.seek(0)
  return 
  
def reset_all_files():
  global csv_files
  for f in csv_files:
    reset_file(get_file(f['type'],'obj'))
  
def create_new_file(obj,user_arr,mapped_obj):
  p = re.compile('\W')
  filename = sys.argv[0].split('.')[0]+'_'+p.sub('',obj['type'])+'_'+uid()+'.csv'
  if os.path.isfile(obj['file']):
    p = re.compile('.csv')
    obj['file'] = p.sub('_'+str(random.randint(0,1000)+'.csv',filename))
  else:
    obj['file'] = filename
  file_obj = open(obj['file'],'w')
  new_file = csv.DictWriter(file_obj,delimiter=',',fieldnames=obj['fields'])
  headers = {}
  for n in new_file.fieldnames:
    headers[n] = n
  new_file.writerow(headers)
  log(0,'----- Begin '+obj['type']+' creation:')
  for u in user_arr:
    if u[' USER ID'] == ' USER ID':
      continue
    b_empty = False
    o = {}
    user_groups = iter(mapped_obj['user_group'])
    dm = get_dn_match(u,mapped_obj['dn_list'])
    if len(dm) == 0:
      continue
    for f in new_file.fieldnames:
      if f == 'User ID' or f == 'USER ID' or f == 'OWNER USER ID' or f == 'DIGEST USER':
        o[f] = u[' USER ID'][:30]
      elif f == 'Device' or f == 'Device Name' or f == 'PRIMARY PHONE':
        o[f] = dm['Device Name'][:15]
      elif f == 'Location' or f == 'LOCATION':
	o[f] = dm['Location']
      elif f == 'Directory Number' or f == 'Directory Number '+dm['cnt']:
        o[f] = dm['Directory Number']
      elif f == 'Partition' or f == 'Route Partition '+dm['cnt']:
        o[f] = dm['Route Partition']
      elif f  == 'Alerting Name' or f == 'Alerting Name '+dm['cnt']:
        o[f] = dm['Alerting Name']
      elif f == 'ASCII Alerting Name' or f == 'ASCII Alerting Name '+dm['cnt']:
        o[f] = dm['ASCII Alerting Name']
      elif f == 'Display' or f == 'Display '+dm['cnt']:
        o[f] = dm['Display']
      elif f == 'ASCII Display' or f == 'ASCII Display '+dm['cnt']:
        o[f] = dm['ASCII Display']
      elif f == 'SUBSCRIBE CALLING SEARCH SPACE' or f == 'Line CSS '+dm['cnt']:
        o[f] = dm['CSS']
      elif f == 'PRESENCE GROUP':
        o[f] = mapped_obj['presence_group'][-1]
      elif f == 'USER GROUP 1' or f == 'USER GROUP 2' or f == 'USER GROUP 3' or f == 'USER GROUP 4':
        try:
          o[f] = user_groups.next()
	except:
          o[f] = ''
      elif f == 'Enable CUP' or f == 'Enable CUPC' or f == 'ALLOW CONTROL OF DEVICE FROM CTI' or f == 'Enable MOC':
        o[f] = 't'
      elif f == 'MAC ADDRESS':
        if obj['type'] == 'CUPC Softphone Adjunct' or obj['type'] == 'CUPC Softphone Standalone':
          prefix = 'UPC'
	elif obj['type'] == 'Android Softphone Adjunct' or obj['type'] == 'Android Softphone Standalone':
          prefix = 'BOT'
	elif obj['type'] == 'iPhone Softphone Adjunct' or obj['type'] == 'iPhone Softphone Standalone':
	  prefix = 'TCT'
	else:
          prefix = 'SEP'
        o[f] = make_softphone_name(prefix,u[' USER ID'])
      elif f == 'XML':
        o[f] = get_pscl_xml(obj['type'])
      elif f == 'DESCRIPTION':
	o[f] = 'Dynamically provisioned '+obj['type']+' for ('+u[' USER ID']+')'
      elif f == 'Unity Profile' or f == 'Meeting Place Profile'or f == 'LDAP Profile'or f == 'CTI Gateway Profile' or f == 'Audio Profile' or f == 'CCMCIP Profile':
        o[f] = 'Default '+f
      elif f == 'PIN':
        if u[' PIN'].strip() == '' or u[' PIN'].strip() == 'NULL':
          pin = '12345'
	else:
          pin = u[' PIN']
        o[f] = pin
    missing = ''
    if len(o) == 0:  
      log(1,'User object ['+u[' USER ID']+'] does not match any column identifiers ['+dm['cnt']+']')
      missing = 'everyting'
      b_empty = True
    for column in o:
      if o[column].strip() == '':
        missing = missing+','+column
        b_empty =  True
    if b_empty:
      log(1,'Attribute(s) ['+missing[1:]+'] are empty, skipping row for user:['+u[' USER ID']+']')
      continue
    else:
      new_file.writerow(o)
  file_obj.close()
  log(0,'Finished '+obj['type']+' filename:['+filename+']')

def get_pscl_xml(dev):
  o = get_ldap_config()
  #TODO: create the product specific information for both android and iphone, right now it's just android
  if dev == 'Android Softphones':
    prefix = 'BOT'
  elif dev == 'iPhone Softphones':
    prefix = 'TCT'
  ldap_photo = 'http://wwwin.cisco.com/dir/photo/zoom/%%userid%%.jpg'
  ret = ''
  ret = ret + '<cuetLevel>1</cuetLevel>'
  ret = ret + '<cucmDirectoryLookupRulesURL></cucmDirectoryLookupRulesURL>'
  ret = ret + '<cucmApplicationDialRulesURL></cucmApplicationDialRulesURL>'
  ret = ret + '<cucmGSMHandoffPreference>1</cucmGSMHandoffPreference>'
  ret = ret + '<ldapUseLDAPUserAuthentication>1</ldapUseLDAPUserAuthentication>'
  ret = ret + '<ldapServer>'+o['ldap_server_port']+'</ldapServer>'
  ret = ret + '<ldapUseSSL>0</ldapUseSSL>'
  ret = ret + '<ldapSearchBase>'+o['ldap_search']+'</ldapSearchBase>'
  ret = ret + '<ldapFieldMapping></ldapFieldMapping>'
  ret = ret + '<ldapPhoto>'+ldap_photo+'</ldapPhoto>'
  ret = ret + '<dialerEmergencyNumbers></dialerEmergencyNumbers>'
  ret = ret + '<domainName>'+o['domain']+'</domainName>'
  ret = ret + '<wifiNetworks></wifiNetworks>'
  return ret
  
def get_ldap_config():
  o = {}
  p1 = re.compile('(OU=).*?(,DC=)')
  p2 = re.compile('(DC=)')
  p3 = re.compile(',')
  reset_file(get_file('ldap','obj'))
  ldap_file = get_file('ldap')
  for r in ldap_file:
    o['ldap_search'] = r['LDAP SYNCHRONIZATION BASE']
    o['ldap_server_port'] = r['HOST NAME 1'] + ':' + r['LDAP PORT NUMBER 1']
    o['domain'] = p3.sub('.',p2.sub('',p1.sub('',r['LDAP SYNCHRONIZATION BASE'].upper())))
  if len(o) == 0:
    log(1,'Unable to locate any LDAP Directory in ldapFile!')
  return o
  
def make_softphone_name(prefix,user,i=0):
  global softphone_ids
  ret = ''
  tmp = prefix+user
  b_match = False
  for sp in softphone_ids:
    if tmp == sp:
      b_match = True
      i += 1
      new_user = user+str(i)
      if len(new_user) > 12:
	if i < 10:
          new_user = user[:11]+str(i)
        elif i < 99:
          new_user = user[:10]+str(i)
	elif i < 999:
          new_user = user[:9]+str(i)
	elif i < 9999:
          new_user = user[:8]+str(i)
	else:
	  return ''
        ret = make_softphone_name(prefix,new_user,i)
  if not b_match:
    ret = tmp.upper()
    softphone_ids.append(tmp)
  if ret == '' and i == 0:
    log(1,'Unable to create unique softphone id for user:['+user+']')
  return ret
  
def get_cnt(csv_file,key):
  headers = {}
  cnt = 0
  p = re.compile(key)
  for n in csv_file.fieldnames:
    if p.search(n):
      cnt += 1
  return cnt
  
def get_dn_list(phone_file,dn_cnt):
  dn_list = []
  for p in phone_file:
    if p['Device Name'] == 'Device Name':
      continue
    o = {}
    for dnc in range(1,dn_cnt+1):
      o['cnt'] = str(dnc)
      o['Device Name'] = p['Device Name']
      o['Location'] = p['Location']
      o['Directory Number'] = p['Directory Number '+str(dnc)]
      o['Route Partition'] = p['Route Partition '+str(dnc)]
      o['CSS'] = p['Line CSS '+str(dnc)]
      #o['vm'] = p['Voice Mail Profile '+str(dnc)]
      o['Alerting Name'] = p['Alerting Name '+str(dnc)]
      o['ASCII Alerting Name'] = p['ASCII Alerting Name '+str(dnc)]
      o['Display'] = p['Display '+str(dnc)]
      o['ASCII Display'] = p['ASCII Display '+str(dnc)]
      dn_list.append(o)
  return dn_list
  
def make_dn(dn):
  stripped = ''
  # strip out any non E.164 characters that may exist in the DN
  #e164 = '^[1-9]\d{1,14}$'
  e164 = '[^0-9\+]'
  p = re.compile(e164)
  stripped = p.sub('',dn)
  return stripped
  
def get_dn_match(user,dn_list):
  global app_dial_rule
  o = {}
  cnt = 0
  b_adr = False
  cache_dn = ''
  dn = user[' TELEPHONE NUMBER']
  username = user['FIRST NAME'] + ' ' + user[' LAST NAME'] + ' (' + user[' USER ID'] + ')'
  num = make_dn(dn)
  for p in dn_list:
    if num[-len(p['Directory Number']):] == p['Directory Number']:
      cnt += 1
      o = p
      if len(p['Directory Number']) != len(num):
        b_adr = True
	cache_dn = p['Directory Number']
  #TODO: if there is more than one match for this DN, we shouldn't decide .. rather force the user to clean up the data
  if cnt > 1:
    log(1,'There are ['+str(cnt)+'] possible matches for user:['+user[' USER ID']+'] with DN:['+dn+'], cannot pick for you, so skipping row')
    return {}
  elif len(o) == 0:
    log(1, 'No match found for user:['+user[' USER ID']+'] with DN:['+dn+'], cannot provision anything for this user')
    return {}
  elif o['Alerting Name'] == '' or o['ASCII Alerting Name'] == '' or o['Display'] == '' or o['ASCII Display'] == '':
      o['Alerting Name'] = username[:30]
      o['ASCII Alerting Name'] = username[:30]
      o['Display'] = username[:30]
      o['ASCII Display'] = username[:30]
  for i in o:
    if o[i] == '':
      log(1,'User:['+user[' USER ID']+'] Attribute:['+i+'] is invalid, skipping row')
      return {}
  #TODO: if we need to strip, then they need to configure Application Dial Rule for dialing to work
  if b_adr:
    b_match = False
    nbw = num[:len(num)-len(cache_dn)]
    nod = len(num)
    tdr = len(nbw)
    for r in app_dial_rule:
      if r['begin'] == nbw and r['num'] == nod and r['del'] == tdr:
        b_match = True
    if not b_match or len(app_dial_rule) == 0:
      app_dial_rule.append({
        'begin':nbw,
        'num':nod,
        'del':tdr
      })
  return o
  
def print_app_dial_rule():
  global app_dial_rule
  index = 1
  log_str = 'In order for CUPC to dial phones, you need to create '+str(len(app_dial_rule))+' Application Dial Rule(s) in CUCM with:'
  for r in app_dial_rule:
    log_str = log_str + '\n '+str(index)+': Number Begins With: ' + str(r['begin']) + '\n '+str(index)+': Number of Digits: ' + str(r['num']) + '\n '+str(index)+': Total Digits to be Removed: ' + str(r['del'])
    index += 1
  if len(app_dial_rule) != 0:
    log(2,log_str)
  
def get_presence_match(presence):
  ret = []
  for p in presence:
   if p['IS STANDARD PRESENCE GROUP'] == 'IS STANDARD PRESENCE GROUP':
     continue
   if p['IS STANDARD PRESENCE GROUP'] == 't':
     ret.append(p['PRESENCE GROUP NAME'])
  if len(ret) == 0:
    log(1,'No standardy presence group found, will try to use the built-in group')
    ret.append('Standard Presence group')
  return ret
  
def get_group_match(group,role):
  ret = []
  if group != '' and role != '':
    cti_roles = get_cti_roles(role)
    role_cnt = get_cnt(group,'FUNCTION ROLE NAME ')
    for g in group:
      if g['DIR GROUP NAME'] == 'DIR GROUP NAME':
        continue
      for dnc in range(1,role_cnt+1):
        for cti_r in cti_roles:
          if g['FUNCTION ROLE NAME '+str(dnc)] == cti_r:
            ret.append(g['DIR GROUP NAME'])
  if len(ret) == 0:
    log(2,'No user defined groups with appropriate role, using built-in group')
    ret.append('Standard CTI Enabled')
    ret.append('Standard CCM End Users')
    ret.append('Standard CTI Allow Control of Phones supporting Connected Xfer and conf user group') #only if 9900/8900 phone
    ret.append('Standard CTI Allow Control of Phones supporting Rollover Mode') #only if 6900 phone
  return ret
	  
def get_cti_roles(role):
  ret = []
  if role != '':
    resouce_cnt = get_cnt(role,'RESOURCE NAME ')
    for r in role:
      if r['FUNCTION ROLE NAME'] == 'FUNCTION ROLE NAME':
        continue
      for dnc in range(1,resouce_cnt+1):
        if r['RESOURCE NAME '+str(dnc)] == 'CTI Application' and r['PERMISSION '+str(dnc)] == '1':
          ret.append(r['FUNCTION ROLE NAME'])
  if len(ret) == 0:
    log(2,'No user defined roles with appropriate permissions, using built-in role')
    ret.append('Standard CTI Enabled')
  return ret
  
if __name__ == "__main__":
    main(sys.argv[1:])

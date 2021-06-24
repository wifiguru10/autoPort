#!/usr/bin/ipython3 -i

import meraki.aio
import copy
import os
import json 
import pickle
import asyncio

import time
import get_keys as g


class portProfiler:
    db = None
    orgid = None
    netid = None
    profiles = [] #holds all the switch-name profiles, used in update()
    tag_inclusive = 'autoPort'
    tag_ERROR = 'ERROR:' # will have +tag_inclusive, ie "ERROR:autoPort"
    WRITE = False #boolean for read-only/read-write API options

    default_portProfile = { "trigger":{}, "switchProfileId":"", "model": "", 'netid':"", "portConfig" : {}}
    
    allPorts = []
    default_ports = {} 

    #compares JSON objects, directionarys and unordered lists will be equal 
    def compare(self, A, B):
        result = True
        if A == None and B == None: 
            return True
        if not type(A) == type(B): 
            #print(f"Wrong type")
            return False
        try:
            if not type(A) == int and not type(A) == float and not type(A) == bool and not len(A) == len(B): 
                #print(f'Not the same length')
                return False
        except:
            print()
        
        if type(A) == dict:
            for a in A:
                if a in B and not self.compare(A[a],B[a]):
                    return False
        elif type(A) == list:
            for a in A:
                if not a in B:
                    return False
        else:
            if not A == B:
                return False
        return result
    ##END-OF COMPARE

    def getDefaultPort(self,model):
        if model in self.default_ports:
            return self.default_ports[model]
        for tmp in self.default_ports:
            return self.default_ports[tmp]
        print(f'RETURNING NULL for DEFAULT PORT PROFILE')
        return

    async def update(self):
        self.profiles =  await self.db.switch.getOrganizationConfigTemplateSwitchProfiles(self.orgid,self.netid)
        for profile in self.profiles:
            SPid = profile['switchProfileId']
            sw_model =  profile['model']
            profilePorts = await self.db.switch.getOrganizationConfigTemplateSwitchProfilePorts(self.orgid, self.netid, SPid)
            for p in profilePorts:
                if len(p['tags']) > 0 and self.tag_inclusive in p['tags'] and not self.tag_ERROR in p['tags']:
                    trigger = p['name'].replace("'",'"')
                    #print(trigger)
                    
                    tempP = copy.deepcopy(self.default_portProfile)
                    tempP['portConfig'] = copy.deepcopy(p)
                    tempP['switchProfileId'] = SPid
                    tempP['model'] = sw_model
                    tempP['netid'] = self.netid                        
                    try:
                        if trigger == "DEFAULT":
                            self.default_ports[sw_model] = copy.deepcopy(p)
                            self.default_ports[sw_model].pop('portId')
                        else:
                            tempP['trigger'] = json.loads(trigger)
                            self.allPorts.append(tempP)
                    except:
                        p['tags'].append('ERROR:autoPort')
                        try:
                            if self.WRITE: await self.db.switch.updateOrganizationConfigTemplateSwitchProfilePort(self.orgid, self.netid, SPid, **p)
                        except:
                            print(f"Can't update switchport tags for misconfigured TAG")

        return


    def findClientProfile(self, client):
        mac = client['mac']
        oui = client['mac'][:8]
        manufacturer = client['manufacturer']
        name = ""
        if not client == None or len(client['description']) >0:
            name = client['description']
        cdp = ""
        if 'cdp' in client and 'platform' in client['cdp']:
            cdp = client['cdp']['platform']
        lldpName = ""
        lldpDesc = ""
        if 'lldp' in client:
            if 'systemName' in client['lldp']:
                lldpName = client['lldp']['systemName']
            if 'systemDescription' in client['lldp']:
                lldpDesc = client['lldp']['systemDescription']
        os = client['os']

        result = None
        last_trigger = ""
        bypass_profiles = ['os', 'manufacturer']
        print()        
        for test_profile in self.allPorts:
            triggers = test_profile['trigger']
            for t in triggers:
                trigger = t.lower()
                if trigger == "mac":
                    if triggers[t] == mac:
                        return test_profile #MAC match, trumps all
                if trigger == "cdp" and not cdp == "":
                    if triggers[t] in cdp:
                        return test_profile #CDP and LLDP are next
                if trigger == "lldp" and not lldpName == "" and not lldpDesc == "":
                    if triggers[t] in lldpName or triggers[t] in lldpDesc:
                        return test_profile #CDP and LLDP are next
                if trigger == "oui":
                    if triggers[t] == oui:
                        #return test_profile
                        if last_trigger in bypass_profiles: result = None
                        if result == None :
                            result = test_profile
                            last_trigger = "oui"
                if trigger == "manufacturer":
                    if triggers[t] == manufacturer:
                        #return test_profile
                        if result == None :
                            result = test_profile
                            last_trigger = "manufacturer"
                if trigger == "os":
                    if triggers[t] == os:
                        #return test_profile
                        if result == None :
                            result = test_profile
                            last_trigger = "os"
        return result

    def __init__(self, db, write_flag, org_id, netid, tag_inclusive):
        self.db = db
        self.orgid = org_id
        self.netid = netid
        self.tag_inclusive = tag_inclusive
        self.tag_ERROR = self.tag_ERROR + tag_inclusive
        self.WRITE = write_flag
        #self.update()
        #return None

            


        
        


#triggers = json.loads(ports[0]['name'].replace("'",'"'))

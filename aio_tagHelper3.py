#!/usr/bin/ipython3 -i

### tagHelper2 by Nico Darrow

### Description
import sys
import time
import copy
import asyncio
import meraki.aio

from bcolors import bcolors

class tagHelper:
    db = None
    orgs = None #list of just org ids
    orgName = None #dict of org_id:name { <orgid> : "<name>" }
    nets = None # contains a dict of  { <net_id> : [ {<network> , <network>} ] , .. }
    tag_target   = "" #tags the Network as "active"
    orgs_whitelist = [] #usually configured via init()
    last_count = 0
    sync_change = 0

    #Initialize with network_Id
    def __init__(self, db, target, orgs_WL):
        self.db = db
        self.orgs = []
        self.orgName = {}
        self.nets = {}
        self.tag_target = target
        self.orgs_whitelist = copy.deepcopy(orgs_WL)
        #self.sync()
        #return None
    
    def show(self):
        print()
        print(f'\t{bcolors.OKBLUE}TagHelper: target[{bcolors.WARNING}{self.tag_target}{bcolors.OKBLUE}]')
        print()
        print(f'\t\t{bcolors.HEADER}*************[{bcolors.OKGREEN}Orgs in scope{bcolors.HEADER}]*****************')
        print(bcolors.ENDC)
        print()
        #print(self.orgs)
        for o in self.orgName:
            o_name = self.orgName[o]
            print (f'{bcolors.OKGREEN}Organization [{bcolors.BOLD}{o_name}{bcolors.ENDC}{bcolors.OKGREEN}]\tOrg_ID [{bcolors.BOLD}{o}{bcolors.ENDC}{bcolors.OKGREEN}]')
            for n in self.nets:
                name = self.nets[n]['name']
                nid = self.nets[n]['id']
                tags = self.nets[n]['tags']
                if o == self.nets[n]['organizationId']: #if it's the correct org
                    print (f'\t{bcolors.OKGREEN}{bcolors.Dim}Network [{bcolors.ResetDim}{name}{bcolors.Dim}]\tNetID [{bcolors.ResetDim}{nid}{bcolors.Dim}]{bcolors.ENDC}')#\tTags{bcolors.ResetDim}{tags}{bcolors.ENDC}')
                  

        #import copy
            print()
        #print(self.orgName)
        return

    #returns True if there is a network change count
    def hasChange(self):
        if self.sync_change != 0:
            return True
        else:
            return False

    #kicks off all the discovery
    async def sync(self):
        self.last_count=len(self.nets)
        await self.loadOrgs()
        self.sync_change=len(self.nets)-self.last_count
        print(f'Last Count difference= {self.sync_change}')
        return

    async def loadOrg(self, o):
        name = o['name']
        orgID = o['id']
        #print(f'Searching ORG[{name}]')
        if not orgID in self.orgs_whitelist:
            if not len(self.orgs_whitelist) == 0:
                return
        try:
            nets = await self.db.organizations.getOrganizationNetworks(orgID)
            #print(nets)
            for n in nets:
                tags = n['tags']

                #print(f'looking for {self.tag_target}')
                if self.tag_target in tags:
                    #print("found one!*****************************************")
                    #print(n)
                
                    if not orgID in self.orgs: self.orgs.append(orgID)
                    if not orgID in self.orgName:
                        self.orgName[orgID] = o['name']

                    nid = n['id']
                    self.nets[nid] = n
        except AttributeError as e:
            print(e)
        except:
            print(f'ERROR: No API support on Org[{name}] OrgID[{orgID}]')
            print("Unexpected error:", sys.exc_info()[0])
            #raise

    #crawls all available orgs and collects orgs with tagged networks
    async def loadOrgs(self):
        orgs = await self.db.organizations.getOrganizations()
        self.nets = {}
        loadOrgsTasks = [self.loadOrg(o) for o in orgs]
        for task in asyncio.as_completed(loadOrgsTasks):
            await task

        return


    


    


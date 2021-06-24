#!/usr/bin/python3 -i
### AutoPort v1 by Nico Darrow

### Description: 
#       This is a evolution of the autoMAC script that did some basic profiling. This is more automated mechanism for handing automatic port configurations and port templates


#import meraki
import meraki.aio
from datetime import datetime
import time
import copy
import sys,os
import asyncio

from bcolors import bcolors
import configparser
import get_keys as g

import aio_tagHelper3
import aio_portProfiler

async def getNetworkDevices(aiomeraki: meraki.aio.AsyncDashboardAPI, netid):
    try:
        result = await aiomeraki.networks.getNetworkDevices(netid)
    except meraki.AsyncAPIError as e:
        print(f"Meraki API error: {e}")
        return None
    except Exception as e:
        print(f"some other error: {e}")
        return None
    return result

async def getNetworkswitchPortStats(aiomeraki: meraki.aio.AsyncDashboardAPI, serial):
    try:
        result = await aiomeraki.switch.getDeviceSwitchPortsStatuses(serial, timespan=900) #last minute port stat
    except meraki.AsyncAPIError as e:
        print(f"Meraki API error: {e}")
        return serial, None
    except Exception as e:
        print(f"some other error: {e}")
        return serial, None

    return serial, result

async def getDeviceSwitchPorts(aiomeraki: meraki.aio.AsyncDashboardAPI, serial):
    try:
        result = await aiomeraki.switch.getDeviceSwitchPorts(serial) #last minute port stat
    except meraki.AsyncAPIError as e:
        print(f"Meraki API error: {e}")
        return serial, None
    except Exception as e:
        print(f"some other error: {e}")
        return serial, None

    return serial, result

async def getNetworkClients(aiomeraki: meraki.aio.AsyncDashboardAPI, net):
    try:
        result = await aiomeraki.networks.getNetworkClients(net, perPage=1000, total_pages='all', timespan=900) #5 minute sample
    except meraki.AsyncAPIError as e:
        print(f"Meraki API error: {e}")
        return net, None
    except Exception as e:
        print(f"some other error: {e}")
        return net, None

    return net, result

#Main function
async def main():
    
    # client_query() # this queries current org and all client information and builds database
    # exit()

    # Fire up Meraki API and build DB's
   
    log_dir = os.path.join(os.getcwd(), "Logs/")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)


    #db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', print_console=False, output_log=True, log_file_prefix=os.path.basename(__file__)[:-3], log_path='Logs/',) 
    async with meraki.aio.AsyncDashboardAPI(
            api_key=g.get_api_key(),
            base_url="https://api.meraki.com/api/v1",
            output_log=True,
            log_file_prefix=os.path.basename(__file__)[:-3],
            log_path='Logs/',
            print_console=False,
    ) as aiomeraki:
    
        
        #configFile = 'autoPort.cfg'
        #cfg = loadCFG(db,configFile)

        org_id = '121177' #nixnet
        org_id2 = '577586652210266696' #nixlab
        org_id3 = '577586652210266697' # 'G6 Bravo' #
        orgsWL = ['121177','577586652210266696','577586652210266697']

        portTemplate_netid = 'L_577586652210276929'
        tag_inclusive = 'autoPort'
        WRITE = True
        BLINK_LED = False #might increase loop time

        PP = aio_portProfiler.portProfiler(aiomeraki, True, org_id2, portTemplate_netid, tag_inclusive)
        await PP.update()
        th = aio_tagHelper3.tagHelper(aiomeraki, tag_inclusive, orgsWL)
        await th.sync()

        loop = True
        loop_count = 0
        switchStatuses = {} #needs to be set outside the loop
        devices_inscope = []#needs to be outside the loop
        while loop:
            print()
            print(f'\t{bcolors.HEADER}****************************{bcolors.FAIL}START LOOP{bcolors.HEADER}*****************************')
            print(bcolors.ENDC)
            totsec = 0.0
            startTime = time.time()
            loop_count += 1
            print("Running now")

            updateGetNetDevs = False
            if loop_count % 10 == 0:
                print(f'Looking for network and profile changes....')
                await th.sync() #update inscope networks
                th.show()
                await PP.update() #update Port profiles
                switchStatuses = {}
                updateGetNetDevs = True


            #old_online_devices = 
            online_devices = []
            #for o in th.orgs:
            #    stats = db.organizations.getOrganizationDevicesStatuses(o)
            #    for s in stats:
            #        if s['status'] == 'online' or s['status'] == 'alerting':
            #            online_devices.append(s['serial'])

            #every 10 intertions, update devices in scope
            if len(devices_inscope) == 0 or updateGetNetDevs:
                devices_inscope = []
                
                tempStart = time.time()
                devices = []
                networkDeviceTasks = [getNetworkDevices(aiomeraki, net) for net in th.nets]
                for task in asyncio.as_completed(networkDeviceTasks):
                    devices = devices + await task
                    #print(f"finished network: {len(devices)}")
                tempStop = time.time()
                print(f'{bcolors.OKBLUE}GetNet Devices load was {bcolors.WARNING} {round(tempStop-tempStart,2)} {bcolors.OKBLUE}seconds')
                totsec = totsec + round(tempStop-tempStart,2)
                
            
                if len(devices) == 0:
                    continue
                for d in devices:
                    if 'tags' in d and tag_inclusive in d['tags']:
                        #dashboard.devices.blinkNetworkDeviceLeds(n['id'], serial=d['serial'], duration=5, duty=10, period=100 )
                        #tempStart = time.time()
                        #if d['serial'] in online_devices and 
                        if d['model'][:2] == "MS": #SWITCHES ONLY
                        #    if BLINK_LED: db.devices.blinkDeviceLeds(serial=d['serial'], duration=5, duty=10, period=100 )
                            devices_inscope.append(d)
                        #tempStop = time.time()
                        #print(f'Blinking LEDS on[{d["serial"]}] was {round(tempStop-tempStart,2)} seconds')

            print(f'{bcolors.OKBLUE}Devices Inscope:')
            for d in devices_inscope:
                #if not 'name' in d:
                #    print(d)
                #    exit()
                #name = d['name']
                serial = d['serial']
                model = d['model']
                nid = d['networkId']
                fw = d['firmware']
                print(f'\t{bcolors.OKBLUE}Switch[{bcolors.WARNING}{serial}{bcolors.OKBLUE}] Model[{bcolors.WARNING}{model}{bcolors.OKBLUE}] Firmware[{bcolors.WARNING}{fw}{bcolors.OKBLUE}] Network_ID[{bcolors.WARNING}{nid}{bcolors.OKBLUE}]')
            print()
            # sets all switches to "primed"
            # switch_wipe(devices_inscope)

            #Builds a { 'SerialNumber' : [ {'portId':1...}, {'portId':2..} ] } model = {}
            old_switchStatuses = switchStatuses
            switchStatuses = {}
        
            tempStart = time.time()
            switchPortStatsTasks = [getNetworkswitchPortStats(aiomeraki, d['serial']) for d in devices_inscope]
            for task in asyncio.as_completed(switchPortStatsTasks):
                serial, portStats = await task
                switchStatuses[serial] = portStats
                print(f"\t{bcolors.OKBLUE}Finished switch: Serial[{bcolors.WARNING}{serial}{bcolors.OKBLUE}] Length[{bcolors.WARNING}{len(switchStatuses[serial])}{bcolors.OKBLUE}]")
            tempStop = time.time()
            print(f'{bcolors.OKBLUE}SwitchStats load for SN[{bcolors.WARNING}{serial}{bcolors.OKBLUE}] was {bcolors.WARNING}{round(tempStop-tempStart,2)}{bcolors.OKBLUE} seconds')
            totsec = totsec + round(tempStop-tempStart,2)
            
            print()

            switches_to_update = [] #clear it out
            for sn in switchStatuses:
                ports = switchStatuses[sn]
                for i in range(0,len(ports)):
                    if not sn in old_switchStatuses:
                        if not sn in switches_to_update:
                            switches_to_update.append(sn)
                        continue
                    newP = ports[i]
                    newP.pop('usageInKb')
                    newP.pop('trafficInKbps')
                    newP.pop('clientCount')
                    oldP = old_switchStatuses[sn][i]
                    if 'usageInKb' in oldP: oldP.pop('usageInKb')
                    if 'trafficInKbps' in oldP:oldP.pop('trafficInKbps')
                    if 'clientCount' in oldP:oldP.pop('clientCount')
                    if not PP.compare(newP,oldP):
                        #print(f"FALSE!!!! Number {i}")
                        #print(f"-OldP[{oldP}]")
                        #print(f"-NewP[{newP}]")
                        if not sn in switches_to_update:
                            switches_to_update.append(sn)

            print()
            print(f"{bcolors.OKBLUE}Switches to update:{bcolors.WARNING}{switches_to_update}{bcolors.OKBLUE}")            
            print()

            # identify all the ports that we're updating
            ports_inscope = {}
            switchport_sum_inscope = {} # {'serial' : [ '1', '2', '3', '7'] }

            #New switchPorts*********************
            tempStart = time.time()
            switchPortTasks = [getDeviceSwitchPorts(aiomeraki, d) for d in switches_to_update]
            for task in asyncio.as_completed(switchPortTasks):
                serial, ports = await task
                portsIS = 0
                for p in ports:
                    if p['tags'] is not None and tag_inclusive in p['tags']:
                        newPort = p
                        #ports_inscope.append(p)
                        if not serial in ports_inscope: ports_inscope[serial] = []
                        ports_inscope[serial].append(newPort)
                        
                        if not serial in switchport_sum_inscope: switchport_sum_inscope[serial] = []
                        switchport_sum_inscope[serial].append(p['portId'])
                        portsIS += 1

                print(f'\t{bcolors.OKBLUE}Checking switch ports:  Switch [{bcolors.WARNING}{serial}{bcolors.OKBLUE}] PortsInscope[{bcolors.WARNING}{portsIS}{bcolors.OKBLUE}]')
                
            tempStop = time.time()
            print(f'{bcolors.OKBLUE}SwitchPort load for all switches was {bcolors.WARNING}{round(tempStop-tempStart,2)}{bcolors.OKBLUE} seconds')
            totsec = totsec + round(tempStop-tempStart,2)

            print()


            #Default ports not in use
            tempStart = time.time() 
            for sn in ports_inscope:
                isPorts = ports_inscope[sn]
                statsPorts = switchStatuses[sn]
                model = ""
                for d in devices_inscope:
                    if d['serial'] == sn:
                        model = d['model']
                #print(f'Looking for Default Port, model[{model}]')
                defaultP = PP.getDefaultPort(model)
                #print(f'Default Profile[{defaultP}]')
                #print()
                
                for isp in isPorts:
                    for statP in statsPorts:
                        if statP['portId'] == isp['portId']:
                            if statP['status'] == 'Disconnected':
                                if defaultP == None: 
                                    continue
                                if not isp['name'] == defaultP['name'] or not isp['vlan'] == defaultP['vlan']:
                                    try:
                                        if WRITE: 
                                            await aiomeraki.switch.updateDeviceSwitchPort(sn,isp['portId'],**defaultP)
                                            print(f'{bcolors.OKBLUE}DEFAULTING PORT - Switch[{bcolors.WARNING}{sn}{bcolors.OKBLUE}] Port[{bcolors.WARNING}{isp["portId"]}{bcolors.OKBLUE}]')
                                    except:
                                        print(f'Failed trying to default port[{isp}]')
            tempStop = time.time()
            print(f'{bcolors.OKBLUE}Port Defaulting was {bcolors.WARNING}{round(tempStop-tempStart,2)} {bcolors.OKBLUE}seconds')    
            totsec = totsec + round(tempStop-tempStart,2)            

            print()

            port_changes = []
            total_clients = 0
            # new network device function, works at network level instead of querying each switch
            allclients = []
            #New getNetworkClients*********************
            tempStart = time.time()
            getNetworkClientsTasks = [getNetworkClients(aiomeraki, net) for net in th.nets]
            for task in asyncio.as_completed(getNetworkClientsTasks):
                n, clients = await task
                for c in clients:
                    if not c['status'] == "Offline" and c['recentDeviceConnection'] == 'Wired':
                        allclients.append(c)           
                print(f'\t{bcolors.OKBLUE}Detecting Clients in [{bcolors.WARNING}{n}{bcolors.OKBLUE}] Count[{bcolors.WARNING}{len(clients)}{bcolors.OKBLUE}] Allclients Total[{bcolors.WARNING}{len(allclients)}{bcolors.OKBLUE}]')

            tempStop = time.time()
            print(f'{bcolors.OKBLUE}Detecting Clients was [{bcolors.WARNING}{round(tempStop-tempStart,2)}{bcolors.OKBLUE}] seconds')
            totsec = totsec + round(tempStop-tempStart,2)
  
            clients_inscope = []
            for c in allclients:
                if c['recentDeviceSerial'] in ports_inscope: #inscope client?
                    recentSerial = c['recentDeviceSerial']
                    currentPort = None
                    for p in ports_inscope[recentSerial]:
                        if p['portId'] == c['switchport']:
                            currentPort = p
                            break

                    currentStatPort = None
                    
                    for stat in switchStatuses[recentSerial]:
                        if stat['portId'] == c['switchport']:
                            currentStatPort = stat
                            break
                        
                    if currentPort != None:
                        if 'portId' in currentPort and currentPort['portId'] in switchport_sum_inscope[recentSerial]:
                            #print()
                            #print(f'Client found {c}')
                            if 'cdp' in currentStatPort:
                                c['cdp'] = currentStatPort['cdp']
                            if 'lldp' in currentStatPort:
                                c['lldp'] = currentStatPort['lldp']
                            c['currentPortConfig'] = currentPort
                            #print(f'Found Current Port {currentPort}')
                            profiledPort = PP.findClientProfile(c)
                            if not profiledPort == None and 'portConfig' in profiledPort:
                                c['profiledPort'] = profiledPort['portConfig']
                            clients_inscope.append(c)
                            
                        else:
                            print(f'Excluding port {currentPort}')

            print(f'{bcolors.OKBLUE}Clients Inscope:[{bcolors.WARNING}{len(clients_inscope)}{bcolors.OKBLUE}] out of [{bcolors.WARNING}{len(allclients)}{bcolors.OKBLUE}]')
            print()

            for cis in clients_inscope:
                if 'currentPortConfig' in cis and 'profiledPort' in cis:
                    cPortConf = cis['currentPortConfig']
                    if 'portId' in cPortConf: cPortConf.pop('portId')
                    tPortConf = cis['profiledPort']
                    if 'portId' in tPortConf: tPortConf.pop('portId')
                    if not PP.compare(cPortConf, tPortConf):
                        print()
                        print(f'{bcolors.OKBLUE}Client [{bcolors.WARNING}{cis["description"]}{bcolors.OKBLUE}] needs a change')
                        print(f'{bcolors.OKBLUE}Currently [{bcolors.WARNING}{cis["currentPortConfig"]}{bcolors.OKBLUE}]')
                        print(f'{bcolors.OKBLUE}Proposed [{bcolors.WARNING}{cis["profiledPort"]}{bcolors.OKBLUE}]')
                        if WRITE:
                            newPort = cis['profiledPort']
                            try:
                                if WRITE:
                                    await aiomeraki.switch.updateDeviceSwitchPort(cis['recentDeviceSerial'], cis['switchport'], **newPort)
                                    print(f'{bcolors.OKBLUE}WRITING CHANGE- Switch[{bcolors.WARNING}{cis["recentDeviceSerial"]}]{bcolors.OKBLUE} Port[{bcolors.WARNING}{cis["switchport"]}{bcolors.OKBLUE}] Config[{bcolors.WARNING} {newPort}{bcolors.OKBLUE} ]')
                            except:
                                print(f'Could not push config to the port')

                elif 'currentPortConfig' in cis:
                    print(f'{bcolors.WARNING}NO profiled port config returned... needs new profile added!{bcolors.OKBLUE}')
                    print(f'{bcolors.OKBLUE}Client[{bcolors.WARNING}{cis}{bcolors.OKBLUE}]')

                


            #time.sleep(1)
            #await asyncio.sleep(1)

            print()
            endTime = time.time()
            duration = round(endTime-startTime,2)
            totsec = round(totsec,2)
            print(f'\t{bcolors.OKBLUE}API Total Time: {bcolors.WARNING}{totsec}{bcolors.OKBLUE} seconds')
            if duration < 60:
                print(f'\t{bcolors.OKBLUE}Loop completed in {bcolors.WARNING}{duration}{bcolors.OKBLUE} seconds')
            else:
                duration = round(duration / 60,2)
                print(f'\t{bcolors.OKBLUE}Loop completed in {bcolors.WARNING}{duration}{bcolors.OKBLUE} minutes')
            print()
            print(f'\t{bcolors.HEADER}****************************{bcolors.FAIL}END LOOP{bcolors.HEADER}*****************************')
            print(bcolors.ENDC)
            print()
            #if loop_count == 25:
            #    break
        


if __name__ == '__main__':
    start_time = datetime.now()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    #print()
    #try:
    #main()
    #except:
        #print("Unexpected error:", sys.exc_info())
        #raise
     

    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')

# -*- coding: utf-8 -*-
# Copyright 2016 Dravetech AB. All rights reserved.
#
# The contents of this file are licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the
# License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

"""
Napalm driver for Skeleton.

Read https://napalm.readthedocs.io for more information.
"""
import re
from napalm.base import NetworkDriver
from napalm.base.exceptions import (
    ConnectionException,
    SessionLockedException,
    MergeConfigException,
    ReplaceConfigException,
    CommandErrorException,
)

from napalm.base.helpers import textfsm_extractor

from netmiko import ConnectHandler
import textfsm

class OptiswitchDriver(NetworkDriver):
    """Napalm driver for Skeleton."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Constructor."""
        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        if optional_args is None:
            optional_args = {}

        # Cache commands
        self.show_port_details = None
        self.lldp_ports = None

    def _send_command(self, command):
        """Wrapper for self.device.send.command().
        If command is a list will iterate through commands until valid command.
        """
        return self.device.send_command(command)

    def _expand_port_list(self, portlist):
        """ Expand optiswitch portlist, ex 1,4,6-9 """
        ports = []
        if portlist:
            for section in portlist.split(','):
                section = section.strip()
                # Skip empty sections from strings like '5,8,'
                if not section:
                    continue
                m = re.match(r'^(\d+)-(\d+)', section)
                if m:
                    ports += range(int(m.group(1)), int(m.group(2)) + 1)
                else:
                    ports.append(int(section))
        # Should be strings, not ints
        return [str(p) for p in ports]


    def _convert_speed(self, speed):
        """ Convert speed to Mbit (int) """
        m = re.match(r'^(?P<speed>\d+)\s*(?P<prefix>[MG])bps', speed)
        if m:
            speed = int(m.group('speed'))
            if m.group('prefix') == 'G':
                speed *= 1E3
        return speed


    def get_interfaces(self):
        """Get interface list"""
        if not self.show_port_details:
            self.show_port_details = self._send_command('show port details')

        ports = textfsm_extractor(
            self, "show_port_details", self.show_port_details
        )
        interfaces = textfsm_extractor(
            self, "show_interface_detail", self._send_command('show interface detail')
        )
        result = {}
        result.update({
            i['port']:
            {
                'is_up': i['linkstate'] == 'ON',
                'is_enabled': i['adminstate'] == 'ENABLE',
                'description': i['description'],
                'speed': self._convert_speed(i['actualspeed'])

            } for i in ports
        })
        result.update({
            i['vif']:
            {
                'is_up': i['linkstate'] == 'UP',
                'is_enabled': i['active'] == 'Yes',
                'description': i['description'],
                'speed': 0

            } for i in interfaces
        })
        return(result)

    def get_facts(self):
        info = textfsm_extractor(
            self, "show_version", self._send_command('show version')
        )[0]
        interfaces = textfsm_extractor(
            self, "show_interface_detail", self._send_command('show interface detail')
        )

        # Return interface list including virtual interfaces
        interface_list = self._expand_port_list(info['validports'])
        for i in interfaces:
            interface_list.append(i['vif'])

        return {
            'vendor': 'MRV',
            'model': info['model'],
            'serial_number': info['serialnumber'],
            'interface_list': interface_list
        }

    def get_vlans(self):
        vlans = {}
        info = textfsm_extractor(
            self, "show_interface_detail", self._send_command('show interface detail')
        )
        for item in info:
            m = re.match(r'^vif(\d+)', item['vif'])
            if m:
                vlan_id = int(m.group(1))
                # Ignore VLANs higher than 4094 and vifs that are down
                if vlan_id < 4095 and item['linkstate'].lower() == 'up':
                    # Add port and vif to list of interfaces
                    interfaces = self._expand_port_list(item['ports'])
                    interfaces.append(item['vif'])
                    vlans.update({vlan_id: {'name': item['name'], 'interfaces': interfaces}})

        return vlans

    def get_interfaces_ip(self):
        info = textfsm_extractor(
            self, "show_interface_detail", self._send_command('show interface detail')
        )
        ips = {}
        for item in info:
            if item['ipaddress'] and item['ipaddress'] != 'not defined':
                ip, prefix_length = item['ipaddress'].split('/')
                ips.update({
                    item['vif']: {
                        'ipv4': {
                            ip: {
                                'prefix_length': prefix_length.strip()
                            }
                        }
                    }
                })

        return ips

    def get_interfaces_vlans(self):
        ''' return dict as documented at https://github.com/napalm-automation/napalm/issues/919#issuecomment-485905491 '''
        port_info = textfsm_extractor(
            self, "show_port_details", self._send_command('show port details')
        )
        interface_info = textfsm_extractor(
            self, "show_interface_detail", self._send_command('show interface detail')
        )

        result = {}

        # Add ports to results dict
        for port in port_info:
            if port['outboundtagged'] == 'untagged':
                mode = 'access'
            else:
                mode = 'trunk'

            result[port['port']] = {
                'mode': mode,
                'access-vlan': -1,
                'trunk-vlans': [],
                'native-vlan': -1,
                'tagged-native-vlan': False
            }

        # Add interfaces to results dict, populate vlans from vifs
        for interface in interface_info:
            result[interface['vif']] = {
                'mode': 'access',
                'access-vlan': -1,
                'trunk-vlans': [],
                'native-vlan': -1,
                'tagged-native-vlan': False
            }

            m = re.match(r'^vif(\d+)', interface['vif'])
            if m:
                vlan_id = int(m.group(1))
                # Ignore VLANs higher than 4094 and vifs that are down
                if vlan_id < 4095 and interface['linkstate'].lower() == 'up':

                    # Add port and vif to list of interfaces
                    for intf in self._expand_port_list(interface['ports']):
                        if result[intf]['mode'] == 'access':
                            result[intf]['access-vlan'] = vlan_id
                        else:
                            result[intf]['trunk-vlans'].append(vlan_id)

                    result[interface['vif']]['access-vlan'] = vlan_id


        return result

    def _get_lldp_ports(self):
        if self.lldp_ports:
            return self.lldp_ports

        if not self.show_port_details:
            self.show_port_details = self._send_command('show port details')

        ports = textfsm_extractor(
            self, "show_port_details", self.show_port_details
        )

        portnums = [int(d['port']) for d in ports]
        portlist = "{}-{}".format(min(portnums), max(portnums))

        lldp_ports = textfsm_extractor(
            self, "show_lldp_port", self._send_command('show lldp port {}'.format(portlist))
        )

        return lldp_ports

    def get_lldp_neighbors(self):
        lldp_ports = self._get_lldp_ports()

        result = {}
        result.update({
            i['port']: {
                'hostname': i['remotesystemname'],
                'port': i['remoteport'],
            } for i in lldp_ports
        })
        return result

    def get_lldp_neighbors_detail(self, interface=None):
        lldp_ports = self._get_lldp_ports()


        if interface:
            lldp_ports = [d for d in lldp_ports if d['port'] == interface]

        result = {}
        result.update({
            i['port']: {
                'parent_interface': '',
                'remote_chassis_id': i['remotechassisid'],
                'remote_system_name': i['remotesystemname'],
                'remote_port': i['remoteport'],
                'remote_port_description': i['remoteport'],
                'remote_system_description': i['remotesystemdescription'],
                'remote_system_capab': self._lldp_system_capabilities(i['remotesystemcapab']),
                'remote_system_enable_capab': self._lldp_system_enabled_capabilities(i['remotesystemcapab']),
            } for i in lldp_ports
        })

        return result

    def _lldp_system_enabled_capabilities(self, capabilities):
        enabled_capabilities = []
        for cap in self._lldp_valid_system_capabilities():
            if any(cap in s.lower() and 'enabled' in s.lower() for s in capabilities):
                enabled_capabilities.append(cap)

        return enabled_capabilities

    def _lldp_system_capabilities(self, capabilities):
        system_capabilites = []
        for cap in self._lldp_valid_system_capabilities():
            if any(cap in s.lower() for s in capabilities):
                system_capabilites.append(cap)

        return system_capabilites

    def _lldp_valid_system_capabilities(self):
        return [
            'other',
            'repeater',
            'bridge',
            'wlan-access-point',
            'router',
            'telephone',
            'docsis-cable-device',
            'station',
        ]

    def open(self):
        """Implement the NAPALM method open (mandatory)"""
        device_type = 'mrv_optiswitch'
        global_delay_factor = 2
        self.device = ConnectHandler(
            device_type=device_type,
            host=self.hostname,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            conn_timeout=self.timeout,
            global_delay_factor=global_delay_factor)
            #,
            #**self.netmiko_optional_args)
        self.device.enable()

    def close(self):
        """Close connection"""
        self.device.disconnect()

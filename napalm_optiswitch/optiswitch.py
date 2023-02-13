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
import os
import tempfile
import uuid
import socket
import difflib

from napalm.base import NetworkDriver
from napalm.base.helpers import textfsm_extractor
from napalm.base.exceptions import (
    MergeConfigException,
    ReplaceConfigException,
    ConnectionClosedException,
)

from netmiko import ConnectHandler

from .optiswitch_file_transfer import OptiSwitchFileTransfer


class OptiswitchDriver(NetworkDriver):
    """Napalm driver for Skeleton."""

    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """Constructor."""
        self.device = None
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout

        self.merge_candidate = False
        self.replace_candidate = False

        if optional_args is None:
            optional_args = {}

    def _send_linux_command(self, command):
        """wrapper to run commands under linux shell"""
        self.device.send_command("linux", expect_string=r"\$")
        output = self.device.send_command(command, expect_string=r"\$")
        self.device.send_command("exit", expect_string=r"#")
        return output.strip()

    def _send_command(self, command):
        """Wrapper for self.device.send.command().
        If command is a list will iterate through commands until valid command.
        """
        try:
            if isinstance(command, list):
                output = str()
                for cmd in command:
                    print(cmd)
                    output += self.device.send_command(cmd)
            else:
                output = self.device.send_command(command)
            return output.strip()
        except (socket.error, EOFError) as e:
            raise ConnectionClosedException(str(e))
        # return self.device.send_command(command)

    def _send_command_timing(self, command):
        """Wrapper for self.device.send.command_timing().
        If command is a list will iterate through commands until valid command.
        """
        return self.device.send_command_timing(command, delay_factor=1)

    def _expand_port_list(self, portlist):
        """Expand optiswitch portlist, ex 1,4,6-9"""
        ports = []
        if portlist:
            for section in portlist.split(","):
                section = section.strip()
                # Skip empty sections from strings like '5,8,'
                if not section:
                    continue
                m = re.match(r"^(\d+)-(\d+)", section)
                if m:
                    ports += range(int(m.group(1)), int(m.group(2)) + 1)
                else:
                    ports.append(section)
        # Should be strings, not ints
        return [str(p) for p in ports]

    def _convert_speed(self, speed):
        """Convert speed to Mbit (int)"""
        m = re.match(r"^(?P<speed>\d+)\s*(?P<prefix>[MG])bps", speed)
        if m:
            speed = int(m.group("speed"))
            if m.group("prefix") == "G":
                speed *= 1e3
        if not speed:
            speed = -1
        return int(speed)

    def _convert_mtu(self, mtu):
        """convert mtu to int if exists"""
        if mtu.isdigit():
            return int(mtu)
        else:
            return 0

    def get_interfaces(self):
        """Get interface list"""
        show_version = self._send_command("show version")
        version = textfsm_extractor(self, "show_version", show_version)[0]

        show_port_details = self._send_command("show port details")
        ports = textfsm_extractor(self, "show_port_details", show_port_details)

        show_interface_detail = self._send_command("show interface detail")
        interfaces = textfsm_extractor(self, "show_interface_detail", show_interface_detail)
        result = {}
        for port in ports:
            result[port["port"]] = {
                "is_up": port["linkstate"] == "ON",
                "is_enabled": port["adminstate"] == "ENABLE",
                "description": port["description"],
                "speed": self._convert_speed(port["actualspeed"]),
                "mtu": -1,
                "last_flapped": -1.0,
                "mac_address": version["basemac"],
            }
            if port["parent"]:
                if "children" not in result[port["parent"]].keys():
                    result[port["parent"]]["children"] = []
                result[port["parent"]]["children"].append(port["port"])
        result.update(
            {
                i["vif"]: {
                    "is_up": i["linkstate"] == "UP",
                    "is_enabled": i["active"] == "Yes",
                    "description": i["description"],
                    "speed": -1,
                    "mtu": self._convert_mtu(i["mtu"]),
                    "last_flapped": -1.0,
                    "mac_address": i["macaddress"],
                }
                for i in interfaces
            }
        )
        return result

    def get_facts(self):
        show_version = self._send_command("show version")
        info = textfsm_extractor(self, "show_version", show_version)[0]
        show_interface_detail = self._send_command("show interface detail")
        interfaces = textfsm_extractor(self, "show_interface_detail", show_interface_detail)
        show_run_hostname = self._send_command("show run | i hostname")
        hostname = re.search(r"^hostname (\S+)", show_run_hostname).group(1)

        # Return interface list including virtual interfaces
        interface_list = self._expand_port_list(info["validports"])
        for i in interfaces:
            interface_list.append(i["vif"])

        uptime = 0
        if info["uptimedays"]:
            uptime += int(info["uptimedays"]) * 86400
        if info["uptimehours"]:
            uptime += int(info["uptimehours"]) * 3600
        if info["uptimemins"]:
            uptime += int(info["uptimemins"]) * 60

        return {
            "hostname": hostname.split(".")[0],
            "fqdn": hostname if "." in hostname else "false",
            "vendor": "MRV",
            "model": info["model"],
            "serial_number": info["serialnumber"],
            "interface_list": interface_list,
            "os_version": info["masteros"],
            "uptime": uptime,
        }

    def get_vlans(self):
        vlans = {}
        info = textfsm_extractor(
            self, "show_interface_detail", self._send_command("show interface detail")
        )
        for item in info:
            m = re.match(r"^vif(\d+)", item["vif"])
            if m:
                vlan_id = int(item["tag"])
                # Ignore VLANs higher than 4094 and vifs that are down
                if vlan_id < 4095 and item["linkstate"].lower() == "up":
                    # Add port and vif to list of interfaces
                    interfaces = self._expand_port_list(item["ports"])
                    interfaces.append(item["vif"])
                    # Fallback to description if name field not available
                    name = item["name"]
                    if not name:
                        name = item["description"]
                    vlans.update({vlan_id: {"name": name, "interfaces": interfaces}})

        return vlans

    def get_interfaces_ip(self):
        info = textfsm_extractor(
            self, "show_interface_detail", self._send_command("show interface detail")
        )
        ips = {}
        for item in info:
            if item["ipaddress"] and item["ipaddress"] != "not defined":
                ip, prefix_length = item["ipaddress"].split("/")
                ips.update(
                    {item["vif"]: {"ipv4": {ip: {"prefix_length": int(prefix_length.strip())}}}}
                )

        return ips

    def get_interfaces_vlans(self):
        """return dict as documented at
        https://github.com/napalm-automation/napalm/issues/919#issuecomment-485905491"""
        port_info = textfsm_extractor(
            self, "show_port_details", self._send_command("show port details")
        )
        interface_info = textfsm_extractor(
            self, "show_interface_detail", self._send_command("show interface detail")
        )

        result = {}

        # Add ports to results dict
        for port in port_info:
            if port["outboundtagged"] == "untagged":
                mode = "access"
            else:
                mode = "trunk"

            result[port["port"]] = {
                "mode": mode,
                "access-vlan": -1,
                "trunk-vlans": [],
                "native-vlan": -1,
                "tagged-native-vlan": False,
            }

        # Add interfaces to results dict, populate vlans from vifs
        for interface in interface_info:
            result[interface["vif"]] = {
                "mode": "access",
                "access-vlan": -1,
                "trunk-vlans": [],
                "native-vlan": -1,
                "tagged-native-vlan": False,
            }

            m = re.match(r"^vif(\d+)", interface["vif"])
            if m:
                vlan_id = int(interface["tag"])
                # Ignore VLANs higher than 4094 and vifs that are down
                if vlan_id < 4095 and interface["linkstate"].lower() == "up":

                    # Add port and vif to list of interfaces
                    for intf in self._expand_port_list(interface["ports"]):
                        if result[intf]["mode"] == "access":
                            result[intf]["access-vlan"] = vlan_id
                        else:
                            result[intf]["trunk-vlans"].append(vlan_id)

                    result[interface["vif"]]["access-vlan"] = vlan_id

        return result

    def _get_lldp_ports(self):
        show_port_details = self._send_command("show port details")
        ports = textfsm_extractor(self, "show_port_details", show_port_details)

        portnums = [int(d["port"]) for d in ports if re.match(r"^[0-9]", d["port"])]
        portlist = "{}-{}".format(min(portnums), max(portnums))

        lldp_ports = textfsm_extractor(
            self,
            "show_lldp_port",
            self.device.send_config_set(["lldp", "show lldp port {}".format(portlist)]),
        )

        return lldp_ports

    def get_lldp_neighbors(self):
        """on some systems, port description is the ifDescription value and port id is ifIndex.
        on others, description is a value a human has entered for the port, and the id is the
        interface name.

        We're doing our best here to find the most useful value that represents the interface name
        """

        lldp_ports = self._get_lldp_ports()
        port_regex = re.compile(
            r".*ethernet|^\d+$|^\d+\/\d+|^\d+\/[A-Z]\d+|^[A-Z]\d+$|^te|^xe|^ge|^gi",
            re.IGNORECASE,
        )

        result = {}
        for i in lldp_ports:
            if (
                " " not in i["remoteport"]
                and ":" not in i["remoteport"]
                and re.match(port_regex, i["remoteport"])
                or not i["portid"]
            ):
                port = i["remoteport"]
            else:
                port = i["portid"]
            result.update(
                {
                    i["port"]: [
                        {
                            "hostname": i["remotesystemname"],
                            "port": port,
                        }
                    ]
                }
            )
        return result

    def get_lldp_neighbors_detail(self, interface=""):
        lldp_ports = self._get_lldp_ports()

        if interface:
            lldp_ports = [d for d in lldp_ports if d["port"] == interface]

        result = {}
        result.update(
            {
                i["port"]: [
                    {
                        "parent_interface": "",
                        "remote_chassis_id": i["remotechassisid"],
                        "remote_system_name": i["remotesystemname"],
                        "remote_port": i["remoteport"],
                        "remote_port_description": i["remoteport"],
                        "remote_system_description": i["remotesystemdescription"],
                        "remote_system_capab": self._lldp_system_capabilities(
                            i["remotesystemcapab"]
                        ),
                        "remote_system_enable_capab": self._lldp_system_enabled_capabilities(
                            i["remotesystemcapab"]
                        ),
                    }
                ]
                for i in lldp_ports
            }
        )

        return result

    def get_mac_address_table(self):
        show_lt = self._send_command("show lt")
        macaddresses = textfsm_extractor(self, "show_lt", show_lt)

        result = []
        for mac in macaddresses:
            static = False
            if mac["mode"].lower() == "static":
                static = True
            result.append(
                {
                    "mac": str(mac["mac"]),
                    "interface": str(mac["port"]),
                    "vlan": int(mac["vid"]),
                    "static": static,
                    "active": True,
                    "moves": 0,
                    "last_move": float(0),
                }
            )

        return result

    def get_config(self, retrieve="all", sanitized=False):
        """Implementation of get_config for netiron.

        Returns the startup or/and running configuration as dictionary.
        The keys of the dictionary represent the type of configuration
        (startup or running). The candidate is always empty string,
        since optiswitch does not support candidate configuration.
        """

        configs = {
            "startup": "",
            "running": "",
            "candidate": "",
        }

        if retrieve in ("startup", "all"):
            command = "show startup-config"
            output = self._send_command(command)
            configs["startup"] = output

        if retrieve in ("running", "all"):
            command = "show running-config"
            output = self._send_command(command)
            configs["running"] = output

        if retrieve in ("candidate", "all"):
            command = "show conf candidate.conf"
            output = self._send_command(command)
            configs["candidate"] = output

        return configs

    def commit_config(self, message="", revert_in=None):
        """
        Send self.merge_candidate to running-config by executing the commands
        """

        if self.merge_candidate:
            output = self.device.send_config_set(self.merge_candidate.splitlines())
            output += self._send_command("write mem")

        else:
            self._send_command(
                f"copy scp running-config 127.0.0.1 /usr/local/etc/sys candidate.conf {self.username} {self.password}"
            )
            self._send_command("write mem")

    def compare_config(self):
        if not self.replace_candidate:
            raise NotImplementedError("Config compare not supported on merge configs")

        running_config = self._send_command("show running-config")

        # clean up running config and replace candidate
        running_config_list = [
            line.strip()
            for line in running_config.splitlines()
            if line
            and not any(
                line.startswith(excluded_line)
                for excluded_line in [
                    "Building configuration",
                    "Current configuration",
                    "! version",
                ]
            )
        ]
        replace_candidate_list = [
            line.strip() for line in self.replace_candidate.splitlines() if line
        ]

        diff = difflib.unified_diff(running_config_list, replace_candidate_list)
        return "\n".join(diff)

    def discard_config(self):
        self.merge_candidate = False
        self.replace_candidate = False

    def load_merge_candidate(self, filename=None, config=None):
        if filename and config:
            raise MergeConfigException("Cannot specify both filename and config")

        if filename:
            with open(filename, "r") as stream:
                self.merge_candidate = stream.read()

        if config:
            self.merge_candidate = config

    def load_replace_candidate(self, filename=None, config=None):
        if filename and config:
            raise ReplaceConfigException("Cannot specify both filename and config")

        if filename:
            with open(filename, "r") as stream:
                self.replace_candidate = stream.read()

        if config:
            self.replace_candidate = config

        tmp_file = self._create_tmp_file(self.replace_candidate)

        with OptiSwitchFileTransfer(
            ssh_conn=self.device,
            source_file=tmp_file,
            dest_file="candidate.conf",
            direction="put",
            file_system="/usr/local/etc/sys",
        ) as transfer:

            if not transfer.verify_space_available():
                raise ReplaceConfigException("Insufficient space available on target filesystem")

            if not (transfer.check_file_exists() and transfer.compare_md5()):
                transfer.put_file()

            if tmp_file and os.path.isfile(tmp_file):
                os.remove(tmp_file)

            if not transfer.verify_file():
                raise ReplaceConfigException("File transfer to remote device failed")

    def _lldp_system_enabled_capabilities(self, capabilities):
        enabled_capabilities = []
        for cap in self._lldp_valid_system_capabilities():
            if any(cap in s.lower() and "enabled" in s.lower() for s in capabilities):
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
            "other",
            "repeater",
            "bridge",
            "wlan-access-point",
            "router",
            "telephone",
            "docsis-cable-device",
            "station",
        ]

    @staticmethod
    def _create_tmp_file(config):
        """Write temp file and for use with and SCP."""
        tmp_dir = tempfile.gettempdir()
        rand_fname = str(uuid.uuid4())
        filename = os.path.join(tmp_dir, rand_fname)
        with open(filename, "wt") as fobj:
            fobj.write(config)
        return filename

    def open(self):
        """Implement the NAPALM method open (mandatory)"""
        device_type = "mrv_optiswitch"
        global_delay_factor = 2
        self.device = ConnectHandler(
            device_type=device_type,
            host=self.hostname,
            username=self.username,
            password=self.password,
            timeout=self.timeout,
            conn_timeout=self.timeout,
            global_delay_factor=global_delay_factor,
        )
        # ,
        # **self.netmiko_optional_args)
        self.device.enable()

    def close(self):
        """Close connection"""
        self.device.disconnect()

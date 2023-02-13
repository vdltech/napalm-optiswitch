# napalm-optiswitch

Napalm Driver for MRV/Adva Optiswitch devices

## Supported functions

* get_facts
* get_interfaces
* get_interfaces_ip
* get_lldp_neighbors
* get_lldp_neighbors_detail
* get_vlans
* get_interfaces_vlans
* get_mac_address_table
* get_config
* load_merge_candidate
* load_replace_candidate
* compare_config
* discard_config
* commit_config

## Supported Models

* OptiSwitch 904
* OptiSwitch 906
* OptiSwitch 940
* OptiSwitch V8


## Replacing configs

The OptiSwitch platform does not allow direct replacement of running config. If using `load_replace_config`, the config file will be applied line by line. The resulting running config may not match the candidate config sent.
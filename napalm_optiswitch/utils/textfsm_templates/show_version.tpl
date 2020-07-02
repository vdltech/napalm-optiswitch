Value Model (OptiSwitch \S+)
Value ValidPorts ([\d\-]+)
Value SerialNumber (\d+)
Value MasterOS (\S+\s\(\d+\))

Start
  ^MRV ${Model}
  ^Unit serial number\s+: ${SerialNumber}
  ^Valid ports: ${ValidPorts}
  ^MasterOS version: ${MasterOS}


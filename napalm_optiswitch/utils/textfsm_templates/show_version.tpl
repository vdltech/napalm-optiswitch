Value Model ((\S+ )?OptiSwitch \S+)
Value ValidPorts ([\d\-]+)
Value SerialNumber (\d+)
Value MasterOS (.*)
Value BaseMAC (\S+)
Value UptimeDays (\d+)
Value UptimeHours (\d+)
Value UptimeMins (\d+)


Start
  ^(MRV|ADVA) ${Model}
  ^Unit serial number\s+: ${SerialNumber}
  ^Valid ports: ${ValidPorts}
  ^MasterOS version: ${MasterOS}
  ^Base MAC address: ${BaseMAC}
  ^up (${UptimeDays} days)?\s+${UptimeHours}:${UptimeMins}


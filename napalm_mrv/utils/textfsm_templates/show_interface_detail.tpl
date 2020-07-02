Value Vif (vif\d+)
Value Name (\S+)
Value Ports ([\d,]+)
Value MacAddress (\S+)
Value IpAddress (\d+\.\d+\.\d+\.\d+/\d+)

Start
  ^${Vif} is (UP|DOWN)
  ^\s+Name: ${Name}
  ^\s+Ports: ${Ports}
  ^\s+MAC address is ${MacAddress}
  ^\s+IP address is ${IpAddress} -> Record
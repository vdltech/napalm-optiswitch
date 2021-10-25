Value Vif (vif\d+|eth\d+)
Value Name (\S+)
Value Ports (\S+)
Value MacAddress (\S+)
Value IpAddress (.*)
Value LinkState (UP|DOWN)
Value Active (Yes|No)
Value Description (.*)
Value MTU (\d+)

Start
  ^${Vif} is ${LinkState}
  ^\s+Name: ${Name}
  ^\s+Description: ${Description}
  ^\s+Active: ${Active}
  ^\s+Ports: ${Ports}
  ^\s+MAC address is ${MacAddress}
  ^\s+IP address is ${IpAddress}
  ^\s+MTU:\s+${MTU} -> Record

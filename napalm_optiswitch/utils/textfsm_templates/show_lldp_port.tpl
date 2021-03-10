Value Port (\d+)
Value Required RemoteChassisId (\S+)
Value PortId (\S+)
Value RemotePort (\S+)
Value RemoteSystemName (\S+)
Value RemoteSystemDescription (.*)
Value List RemoteSystemCapab (.*)

Start
  ^\s+Port ${Port}
  ^Chassis id\s+: ${RemoteChassisId}
  ^Port id\s+: ${PortId}
  ^Port Description\s+: ${RemotePort}
  ^System name\s+: ${RemoteSystemName}
  ^System description\s+: ${RemoteSystemDescription}
  ^System Capabilities :
  ^\s+${RemoteSystemCapab} -> Continue
  ^Management address -> Record

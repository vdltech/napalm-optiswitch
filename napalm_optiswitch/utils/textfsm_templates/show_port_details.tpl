Value Description (.*)
Value LinkState (ON|OFF)
Value AdminState (ENABLE|DISABLE)
Value Port (\d+)
Value ActualSpeed (\d+ [MG]bps)
Value OutBoundTagged (\w+)

Start
  ^Port ${Port} details:
  ^Description\s+: <${Description}>
  ^Link\s+: ${LinkState}
  ^Actual speed\s+:\s+${ActualSpeed}
  ^State\s+: ${AdminState}
  ^OutBound Tagged\s+: ${OutBoundTagged} -> Record

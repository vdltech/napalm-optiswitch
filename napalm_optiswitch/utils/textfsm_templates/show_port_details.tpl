Value Description (.*)
Value LinkState (ON|OFF)
Value AdminState (ENABLE|DISABLE)
Value Port (\S+)
Value ActualSpeed (\d+ [MG]bps)
Value OutBoundTagged (\w+)

Start
  ^(?:Trunk \S+ )?(Port|Trunk) ${Port} details:
  ^Description\s+: ${Description}
  ^Link\s+: ${LinkState}
  ^Actual speed\s+:\s+${ActualSpeed}
  ^State\s+: ${AdminState}
  ^OutBound Tagged\s+: ${OutBoundTagged} -> Record

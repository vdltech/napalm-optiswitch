Value Description (.*)
Value LinkState (ON|OFF)
Value AdminState (ENABLE|DISABLE)
Value Port (\S+)
Value ActualSpeed (\d+\s*[MG]bps)
Value OutBoundTagged (\w+)
Value Parent (\S+)

Start
  ^(?:Trunk ${Parent}, )?(Port|Trunk) ${Port} details:
  ^Description\s+:(\s+)?${Description}
  ^Link\s+:(\s+)?${LinkState}
  ^Actual speed\s+:\s+${ActualSpeed}
  ^State\s+:(\s+)?${AdminState}
  ^OutBound Tagged\s+:(\s+)?${OutBoundTagged} -> Record

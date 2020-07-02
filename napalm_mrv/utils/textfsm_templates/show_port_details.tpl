Value Description (.*)
Value LinkState (ON|OFF)
Value AdminState (ENABLE|DISABLE)
Value Port (\d+)

Start
  ^Port ${Port} details:
  ^Description\s+: <${Description}>
  ^Link\s+: ${LinkState}
  ^State\s+: ${AdminState} -> Record


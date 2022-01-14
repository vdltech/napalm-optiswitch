Value Port (\d+)
Value Vendor ([^\s]*)
Value Model ([^\s]*)


Start
  ^\s+Port[ \t]*${Port}.*SFP EEPROM Parameters
  ^\s+Vendor name is ${Vendor}
  ^\s+Vendor PN is ${Model} -> Record